from openai import OpenAI
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.common_utils import read_file_safely

# 加载环境变量
load_dotenv()

DOUBAO_MODEL_THINKING = "doubao-seed-1-6-thinking-250715"
VOLCENGINE_API_KEY = os.getenv('VOLCENGINE_API_KEY')

# 检查API密钥是否存在
if not VOLCENGINE_API_KEY:
    print("错误: 未找到环境变量 VOLCENGINE_API_KEY")
    sys.exit(1)

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=VOLCENGINE_API_KEY,
)

def compare_news():
    """比较新闻内容"""
    # 读取文件
    summary_chunks_file = os.path.join(os.path.dirname(__file__), "..", "files", "latest_summary_chunks.md")
    combined_news_file = os.path.join(os.path.dirname(__file__), "combined_news.md")
    
    summary_chunks_content = read_file_safely(summary_chunks_file, "RSS摘要")
    combined_news_content = read_file_safely(combined_news_file, "整合新闻")
    
    # 检查文件内容
    if not summary_chunks_content and not combined_news_content:
        print("错误: 两个文件都无法读取或为空")
        return
    
    if not summary_chunks_content:
        print("警告: RSS摘要文件为空，将使用空内容进行比较")
    
    if not combined_news_content:
        print("警告: 整合新闻文件为空，将使用空内容进行比较")
    
    # 构建提示词
    prompt_text = f"""你是一名资深的新闻编辑，请基于以下两段新闻总结：输出在第二段新闻有提到，但在第一段新闻没有提到的内容。

    要求：
    1. 仔细比较两段内容
    2. 只输出第二段独有的信息点
    3. 按重要性排序
    4. 用简洁的要点形式呈现
    5. 如果没有独有内容，请明确说明

    ---
    第一段新闻（RSS摘要）：
    {summary_chunks_content if summary_chunks_content else "[内容为空]"}

    ---
    第二段新闻（整合新闻）：
    {combined_news_content if combined_news_content else "[内容为空]"}
    """
    
    # 调用API
    try:
        print("\n开始调用大模型API进行比较分析...")
        response = client.chat.completions.create(
            model=DOUBAO_MODEL_THINKING,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.3,
        )
        
        final_content = response.choices[0].message.content
        
        # 输出结果
        print("\n=== 比较分析结果 ===")
        print(final_content)
        
        # 保存结果到文件
        output_file = os.path.join(os.path.dirname(__file__), "comparison_result.md")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# RSS摘要与整合新闻比较分析\n\n")
                f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"## 分析结果\n\n{final_content}\n")
            print(f"\n结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存结果文件失败: {e}")
        
    except Exception as e:
        print(f"调用大模型API失败: {e}")
        return

def combine_news(news_files):
    """聚合所有新闻内容"""
    print("\n开始聚合新闻内容...")
    
    # 存储所有成功读取的新闻内容
    combined_content = []
    successful_files = []
    
    # 读取所有新闻文件
    for news_file in news_files:
        content = read_file_safely(news_file["path"], news_file["name"])
        if content:
            combined_content.append({
                "name": news_file["name"],
                "source": news_file["source"],
                "content": content
            })
            successful_files.append(news_file["name"])
    
    # 检查是否有内容可以聚合
    if not combined_content:
        print("错误: 没有找到任何可读取的新闻文件")
        return
    
    print(f"成功读取 {len(combined_content)} 个新闻文件: {', '.join(successful_files)}")
    
    # 构建聚合后的内容
    aggregated_text = "# 加密货币新闻聚合报告\n\n"
    aggregated_text += f"**聚合时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    aggregated_text += f"**数据源**: {', '.join([item['source'] for item in combined_content])}\n\n"
    
    # 添加各个来源的内容
    for i, item in enumerate(combined_content, 1):
        aggregated_text += f"## {i}. {item['name']} ({item['source']})\n\n"
        aggregated_text += f"{item['content']}\n\n"
        aggregated_text += "---\n\n"
    
    # 使用AI进行内容整合和去重
    integration_prompt = f"""你是一名专业的新闻编辑，请将以下来自不同AI源的加密货币新闻进行整合：

    要求：
    1. 以markdown格式输出
    2. 将新闻进行主题聚类，每个聚类需要一个简洁的主题标题（用###开头）
    3. 总结每个聚类的主旨，风格要求公正、客观、简洁（用 **总结** 开头）
    4. 在每个聚类下，用无序列表列出原始新闻的标题和链接（用 **参考** 开头）   

    原始内容：
    {aggregated_text}

    请输出整合后的新闻报告："""
    
    try:
        print("\n开始使用AI整合新闻内容...")
        response = client.chat.completions.create(
            model=DOUBAO_MODEL_THINKING,
            messages=[{"role": "user", "content": integration_prompt}],
            temperature=0.3,
        )
        
        integrated_content = response.choices[0].message.content
        
        # 输出结果
        print("\n=== 新闻聚合结果 ===\n")
        print(integrated_content)
        
        # 保存聚合结果到文件
        output_file = os.path.join(os.path.dirname(__file__), "combined_news.md")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(integrated_content)
            print(f"\n聚合结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存聚合结果失败: {e}")
            
        # 同时保存原始聚合内容（备份）
        raw_output_file = os.path.join(os.path.dirname(__file__), "combined_news_raw.md")
        try:
            with open(raw_output_file, "w", encoding="utf-8") as f:
                f.write(aggregated_text)
            print(f"原始聚合内容已保存到: {raw_output_file}")
        except Exception as e:
            print(f"保存原始聚合内容失败: {e}")
            
    except Exception as e:
        print(f"AI整合失败: {e}")
        print("将直接保存原始聚合内容...")
        
        # 如果AI整合失败，直接保存原始聚合内容
        fallback_file = os.path.join(os.path.dirname(__file__), "combined_news_fallback.md")
        try:
            with open(fallback_file, "w", encoding="utf-8") as f:
                f.write(aggregated_text)
            print(f"原始聚合内容已保存到: {fallback_file}")
        except Exception as e:
            print(f"保存失败: {e}")

if __name__ == "__main__":
    # 定义要聚合的新闻文件列表（可扩展）
    news_files = [
        {
            "name": "豆包BTC新闻",
            "path": os.path.join(os.path.dirname(__file__), "btc_news_from_doubao.md"),
            "source": "豆包AI"
        },
        {
            "name": "OpenAI BTC新闻", 
            "path": os.path.join(os.path.dirname(__file__), "btc_news_from_openai.md"),
            "source": "OpenAI"
        }
    ]
    combine_news(news_files)

    # 对比整合后的新闻与RSS摘要
    compare_news()