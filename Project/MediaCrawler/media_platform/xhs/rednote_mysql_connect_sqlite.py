import mysql.connector
import sqlite3
import logging
from datetime import datetime
import os
import re

# MySQL 连接详细信息 (请替换为您的实际凭据)
MYSQL_CONFIG = {
    'host': 'localhost',        # 您的 MySQL 服务器地址
    'user': 'root',        # 您的 MySQL 用户名
    'password': 'Wot...paas21',# 您的 MySQL 密码
    'database': 'media_crawler' # 包含 xhs_note 表的数据库名称
}
MYSQL_TABLE_NAME = 'xhs_note' # 要从中迁移数据的 MySQL 表名

# SQLite 数据库文件路径 (请替换为实际的 SQLite 文件路径)
# 如果 SQLite 文件在另一个项目中，请提供完整路径或正确的相对路径。
# 示例 (macOS/Linux): SQLITE_PATH = '/Users/你的用户名/项目/另一个Django项目/db.sqlite3'
# 示例 (Windows): SQLITE_PATH = 'C:\\Users\\你的用户名\\项目\\另一个Django项目\\db.sqlite3'
# 示例 (相对路径): SQLITE_PATH = '../另一个项目/db.sqlite3'
SQLITE_PATH = '/Users/wyt/Desktop/NextGen-AI/Project/db/database.sqlite3'
SQLITE_TABLE_NAME = 'rednote_content' # 目标 SQLite 表名 (根据 Django 模型 Meta 类中的 db_table)

# 测试模式 - 只处理前2条记录
TEST_MODE = False
TEST_RECORD_COUNT = 2

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_data():
    """
    将数据从 MySQL xhs_note 表迁移到 SQLite rednote_content 表，
    测试模式下只处理前2条记录。
    """
    # 检查 SQLite 文件是否存在
    if not os.path.exists(SQLITE_PATH):
        logger.error(f"未找到 SQLite 数据库文件: {SQLITE_PATH}")
        logger.error("请确保 SQLITE_PATH 配置正确。")
        return

    mysql_conn = None
    sqlite_conn = None

    try:
        # 连接到 MySQL
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor(dictionary=True) # 以字典形式获取行数据
        print(f"成功连接到 MySQL 数据库: {MYSQL_CONFIG['database']}。")

        # 连接到 SQLite
        sqlite_conn = sqlite3.connect(SQLITE_PATH)
        sqlite_cursor = sqlite_conn.cursor()
        print(f"成功连接到 SQLite 数据库: {SQLITE_PATH}")

        # 从 SQLite rednote_content 表中获取已存在的 thread_id
        sqlite_cursor.execute(f"SELECT thread_id FROM {SQLITE_TABLE_NAME}")
        existing_thread_ids = {row[0] for row in sqlite_cursor.fetchall()}
        print(f"在 SQLite 表 {SQLITE_TABLE_NAME} 中找到 {len(existing_thread_ids)} 个已存在的 thread_id。")

        # 从 MySQL xhs_note 表中获取数据
        if TEST_MODE:
            mysql_cursor.execute(f"SELECT * FROM {MYSQL_TABLE_NAME} LIMIT {TEST_RECORD_COUNT}")
            print(f"测试模式：只获取前 {TEST_RECORD_COUNT} 条记录进行迁移。")
        else:
            mysql_cursor.execute(f"SELECT * FROM {MYSQL_TABLE_NAME}")
        
        mysql_records = mysql_cursor.fetchall()
        print(f"从 MySQL 表 {MYSQL_TABLE_NAME} 中获取了 {len(mysql_records)} 条记录。")

        if not mysql_records:
            print("MySQL 中没有需要迁移的记录。")
            return

        records_to_insert = []
        skipped_due_to_existence = 0
        skipped_due_to_error = 0
        skipped_due_to_short_content = 0

        for record in mysql_records:
            thread_id = record.get('note_id')

            if not thread_id:
                logger.warning(f"因缺少 'note_id' 跳过记录: {record}")
                skipped_due_to_error += 1
                continue

            if thread_id in existing_thread_ids:
                skipped_due_to_existence += 1
                continue # 如果 thread_id 已存在，则跳过此记录

            # 检查内容长度和质量
            content_val = record.get('desc')
            title_val = record.get('title', '')
            
            # 跳过空内容
            if content_val is None:
                if TEST_MODE:
                    print(f"跳过记录 {thread_id}: 内容为空")
                skipped_due_to_short_content += 1
                continue
            
            content_str = str(content_val)
            
            # 移除话题标签后检查实际内容长度
            topic_pattern = r'#[^#]+\[话题\]#'
            clean_content = re.sub(topic_pattern, '', content_str).strip()
            
            # 计算话题标签占比
            total_length = len(content_str)
            topic_length = total_length - len(clean_content)
            topic_ratio = topic_length / total_length if total_length > 0 else 0
            
            # 以下情况跳过：
            # 1. 清洗后内容长度小于100
            # 2. 话题标签占比超过50%且清洗后内容长度小于200
            if len(clean_content) < 300 or (topic_ratio > 0.5 and len(clean_content) < 500):
                if TEST_MODE:
                    print(f"跳过记录 {thread_id}: 内容质量不足")
                    print(f"原内容长度: {total_length}, 清洗后长度: {len(clean_content)}, 话题占比: {topic_ratio:.2%}")
                    print(f"标题: {title_val}")
                    print(f"原内容: {content_str[:100]}{'...' if len(content_str) > 100 else ''}")
                    print(f"清洗后内容: {clean_content[:100]}{'...' if len(clean_content) > 100 else ''}")
                skipped_due_to_short_content += 1
                continue

            # --- 数据映射与转换 ---
            source_val = "rednote" # 根据您的指定

            content_type_mysql = record.get('type')
            if content_type_mysql == 'normal':
                content_type_val = 'note'
            elif content_type_mysql == 'video':
                content_type_val = 'video'
            else:
                content_type_val = None # 或者设置为 'unknown' 等默认值
                print(f"MySQL type '{content_type_mysql}' 未知 (note_id: {thread_id})。将 content_type 设置为 None。")
            
            author_name_val = record.get('nickname')
            # 使用MySQL中的time字段（毫秒时间戳）
            time_ms = record.get('time')
            if time_ms:
                try:
                    # 毫秒时间戳转换为秒级时间戳再转为datetime
                    timestamp_sec = int(time_ms) / 1000
                    created_at_val = datetime.fromtimestamp(timestamp_sec).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"转换time时间戳 {time_ms} -> {created_at_val}")
                except (ValueError, TypeError) as e:
                    print(f"时间转换错误: {e}, 使用当前时间代替")
                    created_at_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                print("记录中没有time字段，使用当前时间")
                created_at_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            updated_at_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') # SQLite 兼容的时间戳格式

            thread_title_val = record.get('title')
            metadata_val = None # JSONField 可以接受 None，将在 SQLite 中存储为 NULL

            # 标签映射
            tags_val = record.get('tag_list')
            
            # 点赞数转换为整数 - 处理所有可能的特殊格式
            liked_count_str = record.get('liked_count')
            likes_val = 0
            if liked_count_str is not None:
                try:
                    if isinstance(liked_count_str, str):
                        # 处理 "10+" 或 "1000+" 格式
                        if '+' in liked_count_str:
                            # 移除加号，转为纯数字
                            num_part = liked_count_str.replace('+', '')
                            if '千' in num_part:
                                num_part = num_part.replace('千', '')
                                likes_val = int(float(num_part) * 1000)
                            # 如果还包含"万"，先处理
                            if '万' in num_part:
                                num_part = num_part.replace('万', '')
                                likes_val = int(float(num_part) * 10000)
                            else:
                                likes_val = int(num_part)
                        # 处理 "1.2万" 格式
                        elif '万' in liked_count_str:
                            num_part = liked_count_str.replace('万', '')
                            likes_val = int(float(num_part) * 10000)
                        else:
                            # 处理普通数字
                            likes_val = int(liked_count_str)
                    else:
                        # 直接是数字类型
                        likes_val = int(liked_count_str)
                except ValueError:
                    logger.warning(f"无法将 liked_count '{liked_count_str}' 转换为整数 (note_id: {thread_id})。默认为 0。")
            
            url_val = record.get('video_url') # 从 video_url 映射

            # 只在测试模式下打印详细信息
            if TEST_MODE:
                print(f"\n处理记录 #{len(records_to_insert)+1}:")
                print(f"thread_id: {thread_id}")
                print(f"content_type: {content_type_val} (原值: {content_type_mysql})")
                print(f"author_name: {author_name_val}")
                print(f"thread_title: {thread_title_val}")
                print(f"content长度: {len(str(content_val)) if content_val else 0}字符")
                print(f"tags: {tags_val}")
                print(f"likes: {likes_val} (原值: {liked_count_str})")
                print(f"url: {url_val}")

            # 为 rednote_content 表准备的数据元组
            # 注意：这里的字段顺序需要与下面的 INSERT 语句中的列名顺序完全一致
            # Django模型中的 id 字段是自增主键，由 SQLite 自动处理，不需要在此插入
            data_tuple = (
                source_val,         # source
                content_type_val,   # content_type
                thread_id,          # thread_id
                thread_title_val,   # thread_title
                None,               # parent_id (在 BaseContent 中定义，可为 NULL)
                url_val,            # url (在 BaseContent 中定义)
                author_name_val,    # author_name (在 BaseContent 中定义)
                None,               # comment_id (在 BaseContent 中定义，可为 NULL)
                None,               # commenter_name (在 BaseContent 中定义，可为 NULL)
                content_val,        # content (在 BaseContent 中定义)
                created_at_val,     # created_at (在 BaseContent 中定义)
                updated_at_val,     # updated_at (在 BaseContent 中定义)
                metadata_val,       # metadata (在 BaseContent 中定义, JSONField)
                tags_val,           # tags (RednoteContent特有)
                likes_val,          # likes (RednoteContent特有)
                None                # embedding_key (在 RedditContent 中定义，可为 NULL)
            )
            records_to_insert.append(data_tuple)
            existing_thread_ids.add(thread_id) # 将已准备插入的 thread_id 加入集合，防止同一批次内重复

        if skipped_due_to_existence > 0:
             print(f"因 thread_id 已存在于 SQLite 中，跳过了 {skipped_due_to_existence} 条记录。")

        if skipped_due_to_short_content > 0:
             print(f"因内容长度小于100字符，跳过了 {skipped_due_to_short_content} 条记录。")

        if records_to_insert:
            # 在测试模式下，显示即将插入的数据
            if TEST_MODE:
                print("\n要插入的数据概要：")
                for i, record in enumerate(records_to_insert):
                    print(f"记录 #{i+1}:")
                    print(f"  source: {record[0]}")
                    print(f"  content_type: {record[1]}")
                    print(f"  thread_id: {record[2]}")
                    print(f"  thread_title: {record[3]}")
                    # 省略其他字段以避免输出过多

                # 询问是否继续
                confirm = input("\n数据看起来正确吗？是否继续插入？(y/n): ")
                if confirm.lower() != 'y':
                    print("用户取消了插入操作。")
                    return

            # 构建插入语句，确保列名与 rednote_content 表的实际结构匹配
            insert_query = f"""
                INSERT INTO {SQLITE_TABLE_NAME} (
                    source, content_type, thread_id, thread_title, parent_id, url,
                    author_name, comment_id, commenter_name, content, created_at,
                    updated_at, metadata, tags, likes, embedding_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            try:
                sqlite_cursor.executemany(insert_query, records_to_insert) # 批量插入
                sqlite_conn.commit() # 提交事务
                print(f"成功向 SQLite 表 {SQLITE_TABLE_NAME} 插入 {len(records_to_insert)} 条新记录。")
            except sqlite3.Error as e:
                logger.error(f"批量插入 SQLite 时发生错误: {e}")
                print(f"错误详情: {e}")
                sqlite_conn.rollback() # 如果发生错误，回滚事务
        else:
            print("没有新的记录需要插入到 SQLite。")
        
        if skipped_due_to_error > 0:
            print(f"因缺少 'note_id' 或其他处理错误，跳过了 {skipped_due_to_error} 条记录。")

    except mysql.connector.Error as err:
        logger.error(f"MySQL 错误: {err}")
        print(f"MySQL 错误: {err}")
    except sqlite3.Error as err:
        logger.error(f"SQLite 错误: {err}")
        print(f"SQLite 错误: {err}")
    except Exception as e:
        logger.error(f"发生意外错误: {e}")
        print(f"发生意外错误: {e}")
    finally:
        # 关闭数据库连接
        if mysql_conn and mysql_conn.is_connected():
            mysql_cursor.close()
            mysql_conn.close()
            print("MySQL 连接已关闭。")
        if sqlite_conn:
            sqlite_conn.close()
            print("SQLite 连接已关闭。")

# --- 如何运行此脚本 ---
# 1. 保存代码：将以上代码保存到一个 Python 文件中，例如 `migrate_xhs_to_redditcontent.py`。
#
# 2. 安装必要的库：如果您尚未安装 `mysql-connector-python`，请打开终端或命令提示符运行：
#    pip install mysql-connector-python
#    (Python 内置了 `sqlite3` 模块，通常无需额外安装)
#
# 3. 配置连接信息和路径：
#    - **MySQL 配置**: 在脚本中找到 `MYSQL_CONFIG` 字典，将其中的 'host', 'user', 'password', 和 'database'
#      替换为您的实际 MySQL 服务器信息和数据库名称。
#    - **SQLite 路径**: 在脚本中找到 `SQLITE_PATH` 变量。将其值修改为您目标 SQLite 数据库文件
#      （通常在 Django 项目中名为 `db.sqlite3`）的 **准确文件路径**。
#      *   如果 SQLite 文件位于 **不同的 Django 项目** 中，您必须提供该文件的 **绝对路径** 或
#          从 **当前脚本运行位置** 到该文件的 **正确相对路径**。
#          例如：
#          - 绝对路径 (macOS/Linux): '/Users/您的用户名/代码/其他Django项目/db.sqlite3'
#          - 绝对路径 (Windows): 'C:\\Users\\您的用户名\\代码\\其他Django项目\\db.sqlite3' (注意双反斜杠)
#          - 相对路径: 假设您的脚本位于 `/data_scripts/` 目录下，而 SQLite 文件位于 `/django_projects/another_app/db.sqlite3`，
#            并且 `/data_scripts/` 和 `/django_projects/` 是同级目录，那么相对路径可以是 '../django_projects/another_app/db.sqlite3'。
#
# 4. 从终端运行脚本：
#    - 打开您的终端 (Terminal) 或命令提示符 (Command Prompt)。
#    - 使用 `cd` 命令导航到您保存 `migrate_xhs_to_redditcontent.py` 文件的目录。
#    - 执行脚本：
#      python migrate_xhs_to_redditcontent.py
#
# 5. 查看日志输出：脚本运行时，会在控制台打印日志信息，包括连接状态、获取的记录数、
#    成功插入的记录数、跳过的记录数以及任何可能发生的错误。请仔细检查这些输出。

if __name__ == "__main__":
    print("开始数据迁移过程...")
    migrate_data()
    print("数据迁移过程结束。")