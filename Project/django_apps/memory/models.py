from django.db import models

class SessionMemory(models.Model):
    session_id = models.CharField(max_length=255, unique=True, db_index=True)  # 唯一会话ID
    memory_data = models.JSONField(default=list)  # 存储对话历史的JSON
    updated_at = models.DateTimeField(auto_now=True)  # 最后更新时间

    def add_memory(self, user_input, ai_response):
        """
        添加一条对话记录
        """
        self.memory_data.append({"user": user_input, "ai": ai_response})
        self.save()

    def get_recent_memory(self, limit=5):
        """
        获取最近的对话历史
        """
        return self.memory_data[-limit:]

    def clear_memory(self):
        """
        清空记忆
        """
        self.memory_data = []
        self.save()

    def __str__(self):
        return f"SessionMemory(session_id={self.session_id})"