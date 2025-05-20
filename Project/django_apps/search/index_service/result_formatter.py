from typing import List, Dict

class ResultFormatter:
    @staticmethod
    def format_recommendations(items: List[Dict]) -> str:
        """Format recommendation items into HTML content"""
        if not items:
            return "<p>未找到相关推荐。</p>"

        output_lines = ["<p>根据您的查询，为您推荐以下选项：</p>"]
        output_lines.append('<div class="recommendation-details-card">')

        for i, item in enumerate(items, 1):
            if i > 1:
                output_lines.append('<hr style="margin: 20px 0; border-top: 1px solid #eee;">')

            # 基本信息
            name = item['name'].title()
            avg_rating = item['avg_rating']
            total_upvotes = item['total_upvotes']
            mentions = item['mentions']
            sentiment_counts = item['sentiment_counts']

            # 标题和评分信息
            output_lines.append(f'<h4 style="margin-bottom: 8px; font-size: 1.15em;">{i}. {name}</h4>')
            output_lines.append(
                f'<p style="font-size: 0.9em; color: #555; margin-top: 8px; margin-bottom: 8px;">'
                f'<span>⭐ Rating: {avg_rating:.1f}/5.0</span> '
                f'<span>👍 Upvotes: {total_upvotes}</span> '
                f'<span>📝 Mentions: {mentions}</span>'
                f'</p>'
            )

            # 情感统计
            output_lines.append(
                f'<p style="font-size: 0.9em; color: #555; margin-bottom: 12px;">'
                f"Sentiment: <span class='sentiment-positive'>Positive: {sentiment_counts['positive']}</span>, "
                f"<span class='sentiment-neutral'>Neutral: {sentiment_counts['neutral']}</span>, "
                f"<span class='sentiment-negative'>Negative: {sentiment_counts['negative']}</span>"
                f'</p>'
            )

            # 总结
            output_lines.append("<p style='margin-top: 15px; font-weight: bold;'>General Summary:</p>")
            output_lines.append("<ul>")
            summary = item.get('summary', 'No summary available.')
            summary_points = [s.strip() for s in summary.split('\n') if s.strip()]
            if not summary_points and summary.strip():
                summary_points = [summary.strip()]
            
            if not summary_points:
                output_lines.append("<li>No summary available.</li>")
            else:
                for point in summary_points:
                    output_lines.append(f"<li>{point}</li>")
            output_lines.append("</ul>")

            # 详细评论
            output_lines.append("<p style='margin-top: 15px; font-weight: bold;'>Detailed Reviews:</p>")
            output_lines.append("<ul>")
            posts = item['posts']
            if not posts:
                output_lines.append("<li>No detailed reviews available.</li>")
            else:
                for review in posts[:3]:
                    content = review['content'].replace('\n', '<br />')
                    upvotes = review.get('upvotes', 0)
                    sentiment = review.get('sentiment', 'neutral').lower()
                    output_lines.append(f"<li>{content} ({sentiment}, 👍{upvotes})</li>")
            output_lines.append("</ul>")

        output_lines.append('</div>')

        # 比较表格
        if items:
            output_lines.append('<div class="comparison-table-card">')
            output_lines.append('<h3><strong>Comparison Table</strong></h3>')
            output_lines.append('<table class="comparison-table" border="1" cellspacing="0" cellpadding="0" style="width:100%;">')
            
            # 表头
            output_lines.append('<thead><tr>')
            output_lines.append('<th>Name</th>')
            output_lines.append('<th>Avg. Rating</th>')
            output_lines.append('<th>Total Upvotes</th>')
            output_lines.append('<th>Mentions</th>')
            output_lines.append('</tr></thead>')
            
            # 表格内容
            output_lines.append('<tbody>')
            for item in items:
                output_lines.append(
                    f'<tr>'
                    f'<td>{item["name"].title()}</td>'
                    f'<td>{item["avg_rating"]:.1f}</td>'
                    f'<td>{item["total_upvotes"]}</td>'
                    f'<td>{item["mentions"]}</td>'
                    f'</tr>'
                )
            output_lines.append('</tbody>')
            output_lines.append('</table>')
            output_lines.append('</div>')

        return "".join(output_lines) 