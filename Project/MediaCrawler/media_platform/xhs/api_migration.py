"""
API专用的数据迁移模块
基于原始的rednote_mysql_connect_sqlite.py，但针对API调用进行了优化
"""

import mysql.connector
import sqlite3
import logging
from datetime import datetime
import os
import re
from typing import Dict, Any, Optional

# 使用项目的配置
import config

# MySQL 连接配置
MYSQL_CONFIG = {
    'host': config.RELATION_DB_HOST,
    'user': config.RELATION_DB_USER,
    'password': config.RELATION_DB_PWD,
    'database': config.RELATION_DB_NAME,
    'port': config.RELATION_DB_PORT
}

MYSQL_TABLE_NAME = 'xhs_note'

# SQLite 配置 - 这里需要根据Next-GenAI项目路径调整
SQLITE_PATH = '/Users/wyt/Desktop/NextGen-AI/Project/db/database.sqlite3'
SQLITE_TABLE_NAME = 'rednote_content'

# 配置日志
logger = logging.getLogger(__name__)

def migrate_recent_data(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    迁移最近的数据到SQLite数据库
    
    Args:
        limit: 限制迁移的记录数量，如果为None则迁移所有新数据
        
    Returns:
        包含迁移结果的字典
    """
    # 检查 SQLite 文件是否存在
    if not os.path.exists(SQLITE_PATH):
        error_msg = f"未找到 SQLite 数据库文件: {SQLITE_PATH}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    mysql_conn = None
    sqlite_conn = None
    
    try:
        # 连接到 MySQL
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor(dictionary=True)
        logger.info(f"成功连接到 MySQL 数据库: {MYSQL_CONFIG['database']}")

        # 连接到 SQLite
        sqlite_conn = sqlite3.connect(SQLITE_PATH)
        sqlite_cursor = sqlite_conn.cursor()
        logger.info(f"成功连接到 SQLite 数据库: {SQLITE_PATH}")

        # 获取已存在的 thread_id
        sqlite_cursor.execute(f"SELECT thread_id FROM {SQLITE_TABLE_NAME}")
        existing_thread_ids = {row[0] for row in sqlite_cursor.fetchall()}
        logger.info(f"SQLite表中已存在 {len(existing_thread_ids)} 个thread_id")

        # 从 MySQL 获取最新的数据
        if limit:
            # 获取最新的指定数量的记录
            mysql_cursor.execute(f"""
                SELECT * FROM {MYSQL_TABLE_NAME} 
                ORDER BY id DESC 
                LIMIT {limit}
            """)
        else:
            # 获取所有记录
            mysql_cursor.execute(f"SELECT * FROM {MYSQL_TABLE_NAME}")
        
        mysql_records = mysql_cursor.fetchall()
        logger.info(f"从MySQL获取了 {len(mysql_records)} 条记录")

        if not mysql_records:
            return {"success": True, "message": "没有新数据需要迁移", "migrated_count": 0}

        records_to_insert = []
        skipped_counts = {
            "existing": 0,
            "short_content": 0,
            "missing_data": 0
        }

        for record in mysql_records:
            thread_id = record.get('note_id')
            
            if not thread_id:
                logger.warning(f"记录缺少note_id: {record}")
                skipped_counts["missing_data"] += 1
                continue

            if thread_id in existing_thread_ids:
                skipped_counts["existing"] += 1
                continue

            # 内容质量检查
            content_val = record.get('desc')
            if not content_val:
                skipped_counts["short_content"] += 1
                continue
                
            content_str = str(content_val)
            
            # 移除话题标签后检查内容长度
            topic_pattern = r'#[^#]+\[话题\]#'
            clean_content = re.sub(topic_pattern, '', content_str).strip()
            
            # 计算话题标签占比
            total_length = len(content_str)
            topic_length = total_length - len(clean_content)
            topic_ratio = topic_length / total_length if total_length > 0 else 0
            
            # 内容质量过滤
            if len(clean_content) < 100 or (topic_ratio > 0.5 and len(clean_content) < 200):
                skipped_counts["short_content"] += 1
                continue

            # 数据映射
            source_val = "rednote"
            
            # 内容类型映射
            content_type_mysql = record.get('type')
            content_type_val = 'note' if content_type_mysql == 'normal' else 'video' if content_type_mysql == 'video' else None
            
            author_name_val = record.get('nickname')
            
            # 时间戳转换
            time_ms = record.get('time')
            if time_ms:
                try:
                    timestamp_sec = int(time_ms) / 1000
                    created_at_val = datetime.fromtimestamp(timestamp_sec).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    created_at_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_at_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            updated_at_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            
            # 点赞数转换
            liked_count_str = record.get('liked_count')
            likes_val = 0
            if liked_count_str:
                try:
                    if isinstance(liked_count_str, str):
                        if '+' in liked_count_str:
                            num_part = liked_count_str.replace('+', '')
                            if '万' in num_part:
                                likes_val = int(float(num_part.replace('万', '')) * 10000)
                            else:
                                likes_val = int(num_part)
                        elif '万' in liked_count_str:
                            likes_val = int(float(liked_count_str.replace('万', '')) * 10000)
                        else:
                            likes_val = int(liked_count_str)
                    else:
                        likes_val = int(liked_count_str)
                except ValueError:
                    likes_val = 0

            # 准备插入数据
            data_tuple = (
                source_val,                    # source
                content_type_val,              # content_type
                thread_id,                     # thread_id
                record.get('title'),           # thread_title
                None,                          # parent_id
                record.get('video_url'),       # url
                author_name_val,               # author_name
                None,                          # comment_id
                None,                          # commenter_name
                content_val,                   # content
                created_at_val,                # created_at
                updated_at_val,                # updated_at
                None,                          # metadata
                record.get('tag_list'),        # tags
                likes_val,                     # likes
                None                           # embedding_key
            )
            
            records_to_insert.append(data_tuple)
            existing_thread_ids.add(thread_id)

        # 执行插入
        if records_to_insert:
            insert_query = f"""
                INSERT INTO {SQLITE_TABLE_NAME} (
                    source, content_type, thread_id, thread_title, parent_id, url,
                    author_name, comment_id, commenter_name, content, created_at,
                    updated_at, metadata, tags, likes, embedding_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            sqlite_cursor.executemany(insert_query, records_to_insert)
            sqlite_conn.commit()
            
            logger.info(f"成功插入 {len(records_to_insert)} 条记录")
            
            return {
                "success": True,
                "message": f"成功迁移 {len(records_to_insert)} 条记录",
                "migrated_count": len(records_to_insert),
                "skipped_counts": skipped_counts
            }
        else:
            return {
                "success": True,
                "message": "没有新记录需要迁移",
                "migrated_count": 0,
                "skipped_counts": skipped_counts
            }

    except mysql.connector.Error as err:
        error_msg = f"MySQL错误: {err}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except sqlite3.Error as err:
        error_msg = f"SQLite错误: {err}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"迁移过程中发生错误: {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    finally:
        # 关闭连接
        if mysql_conn and mysql_conn.is_connected():
            mysql_cursor.close()
            mysql_conn.close()
        if sqlite_conn:
            sqlite_conn.close()

if __name__ == "__main__":
    # 测试迁移功能
    print("开始测试数据迁移...")
    result = migrate_recent_data(limit=5)
    print(f"迁移结果: {result}")
