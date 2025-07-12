"""
MediaCrawler API服务
为Next-GenAI项目提供实时搜索功能的API接口
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

# 第三方库
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 项目内部模块
import config
import db
from media_platform.xhs import XiaoHongShuCrawler
from media_platform.xhs.api_migration import migrate_recent_data

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="MediaCrawler API",
    description="为Next-GenAI项目提供实时搜索功能的API接口",
    version="1.0.0"
)

# 添加CORS中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class CrawlRequest(BaseModel):
    query: str = Field(..., description="搜索关键词")
    limit: int = Field(default=5, ge=1, le=20, description="爬取数量，范围1-20")
    platform: str = Field(default="rednote", description="平台名称")

# 响应模型
class CrawlResponse(BaseModel):
    success: bool
    message: str
    query: str
    limit: int
    platform: str
    timestamp: str
    crawled_count: Optional[int] = None
    migrated_count: Optional[int] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    timestamp: str

# 全局变量，用于跟踪当前是否有爬虫任务在运行
_crawling_in_progress = False
_crawling_lock = asyncio.Lock()

async def execute_crawler_with_params(query: str, limit: int) -> Dict[str, Any]:
    """
    执行爬虫任务的核心函数
    
    Args:
        query: 搜索关键词
        limit: 爬取数量
        
    Returns:
        包含爬虫结果信息的字典
    """
    global _crawling_in_progress
    
    # 保存原始配置
    original_keywords = config.KEYWORDS
    original_max_notes = config.CRAWLER_MAX_NOTES_COUNT
    original_headless = config.HEADLESS
    
    try:
        # 动态设置配置
        config.KEYWORDS = query
        config.CRAWLER_MAX_NOTES_COUNT = limit
        config.HEADLESS = True  # API模式下强制使用无头浏览器
        config.PLATFORM = "xhs"
        config.CRAWLER_TYPE = "search"
        
        logger.info(f"开始爬虫任务: 关键词='{query}', 数量={limit}")
        
        # 初始化数据库
        if config.SAVE_DATA_OPTION == "db":
            await db.init_db()
        
        # 创建并启动爬虫
        crawler = XiaoHongShuCrawler()
        await crawler.start()
        
        # 关闭数据库连接
        if config.SAVE_DATA_OPTION == "db":
            await db.close()
            
        logger.info("爬虫任务完成")
        
        return {
            "success": True,
            "crawled_count": limit,
            "message": f"成功爬取 {limit} 条关于 '{query}' 的帖子"
        }
        
    except Exception as e:
        logger.error(f"爬虫任务失败: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "message": f"爬虫任务失败: {str(e)}"
        }
    finally:
        # 恢复原始配置
        config.KEYWORDS = original_keywords
        config.CRAWLER_MAX_NOTES_COUNT = original_max_notes
        config.HEADLESS = original_headless

def execute_data_migration() -> Dict[str, Any]:
    """
    执行数据迁移的函数
    
    Returns:
        包含迁移结果信息的字典
    """
    try:
        logger.info("开始数据迁移...")
        
        # 使用新的迁移函数
        result = migrate_recent_data()
        
        if result["success"]:
            logger.info(f"数据迁移完成: {result['message']}")
        else:
            logger.error(f"数据迁移失败: {result.get('error', '未知错误')}")
            
        return result
        
    except Exception as e:
        logger.error(f"数据迁移异常: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"数据迁移失败: {str(e)}"
        }

async def full_crawl_and_migrate_workflow(query: str, limit: int) -> Dict[str, Any]:
    """
    完整的爬虫+迁移工作流
    
    Args:
        query: 搜索关键词
        limit: 爬取数量
        
    Returns:
        包含完整工作流结果的字典
    """
    global _crawling_in_progress
    
    async with _crawling_lock:
        if _crawling_in_progress:
            return {
                "success": False,
                "error": "另一个爬虫任务正在进行中，请稍后再试",
                "message": "系统忙碌中"
            }
        
        _crawling_in_progress = True
        
        try:
            # 第一步：执行爬虫
            crawl_result = await execute_crawler_with_params(query, limit)
            
            if not crawl_result["success"]:
                return crawl_result
            
            # 第二步：执行数据迁移
            migration_result = execute_data_migration()
            
            # 合并结果
            final_result = {
                "success": crawl_result["success"] and migration_result["success"],
                "query": query,
                "limit": limit,
                "platform": "rednote",
                "timestamp": datetime.now().isoformat(),
                "crawled_count": crawl_result.get("crawled_count"),
                "migrated_count": migration_result.get("migrated_count", 0),
                "message": f"爬虫: {crawl_result['message']}; 迁移: {migration_result['message']}"
            }
            
            if not migration_result["success"]:
                final_result["error"] = migration_result.get("error", "数据迁移失败")
                
            return final_result
            
        finally:
            _crawling_in_progress = False

@app.post("/api/crawl", response_model=CrawlResponse)
async def crawl_rednote(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    接收实时搜索请求，执行爬虫并迁移数据
    
    Args:
        request: 包含搜索参数的请求体
        background_tasks: FastAPI的后台任务管理器
        
    Returns:
        爬虫和迁移的结果
    """
    try:
        logger.info(f"收到爬虫请求: query='{request.query}', limit={request.limit}")
        
        # 参数验证
        if not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="搜索关键词不能为空"
            )
        
        # 执行完整的工作流
        result = await full_crawl_and_migrate_workflow(request.query, request.limit)
        
        if result["success"]:
            return CrawlResponse(**result)
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "爬虫任务失败")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API请求处理失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )

@app.get("/api/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "crawling_in_progress": _crawling_in_progress
    }

@app.get("/api/status")
async def get_status():
    """
    获取服务状态
    """
    return {
        "service": "MediaCrawler API",
        "version": "1.0.0",
        "platform": config.PLATFORM,
        "crawling_in_progress": _crawling_in_progress,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # 检查必要的配置
    if not config.COOKIES:
        logger.warning("警告: COOKIES配置为空，可能影响爬虫效果")
    
    if config.LOGIN_TYPE != "cookie":
        logger.warning("警告: 建议在API模式下使用cookie登录方式")
    
    # 启动API服务
    logger.info("启动MediaCrawler API服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # 改为5000端口
        log_level="info"
    )
