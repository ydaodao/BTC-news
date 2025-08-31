import os
from openai import OpenAI
import my_utils
import lark
from llm_ali import generate_title_and_summary


DOUBAO_MODEL_FLASH = "doubao-seed-1-6-flash-250715"
DOUBAO_MODEL_THINKING = "doubao-seed-1-6-thinking-250715"
# 需要从main.py导入的配置变量
# VOLCENGINE_API_KEY, LOCAL_DEV等需要在调用时传入或从配置文件读取
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'

async def generate_news_summary(start_date: str, end_date: str, fetch_news_with_content, VOLCENGINE_API_KEY):
    """
    生成新闻摘要并调用大模型处理
    """
    processed_news = fetch_news_with_content(start_date, end_date)
    if not processed_news:
        print("没有找到包含正文内容的新闻。")
        return None

    print(f"成功读取 {len(processed_news)} 条新闻内容。")
    print("构建大模型API的Prompt...")
    
    all_content = "\n\n-----\n\n".join([
        f"标题: {n['title']}\n"
        f"真实链接: {n['real_url']}\n"
        f"正文: {n['content']}" 
        for n in processed_news
    ])
    print(f"大模型API的Prompt长度（{my_utils.string_to_bytes(all_content)}KB）...")

    prompt_text = f"""你是一名资深的新闻编辑，请对以下新闻进行处理。你的任务是：

    1. 全文以markdown格式输出
    2. 将所有新闻进行主题聚类，每个聚类需要一个简洁的主题标题。要求：用###开头，序号用一、二、三……来标注，聚类之间用 --- 分隔开
    3. 总结每个聚类的主旨，风格要求公正、客观、简洁。要求：用 **总结** 开头，内容用有序列表呈现
    4. 在每个聚类下，用无序列表列出原始新闻的标题和链接，符合markdown格式[标题](url)。要求：用 **参考** 开头

    以下是新闻内容：

    -----

    {all_content}
    """

    # 保存 prompt 到文件
    prompt_file = os.path.join(os.path.dirname(__file__), "latest_prompt.txt")
    try:
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt_text)
        print(f"Prompt 已保存到: {prompt_file}")
        
        # 可选：自动打开文件
        # os.startfile(prompt_file)
    except Exception as e:
        print(f"保存 Prompt 失败: {e}")

    print("开始调用火山引擎API生成摘要...")
    try:
        # # 根据环境设置代理
        # if PROXIES:
        #     os.environ['HTTP_PROXY'] = PROXIES['http']
        #     os.environ['HTTPS_PROXY'] = PROXIES['https']

        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=VOLCENGINE_API_KEY,
        )

        response = client.chat.completions.create(
            model=DOUBAO_MODEL_FLASH,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.3,
        )

        summary_content = response.choices[0].message.content

        # 保存响应内容到文件
        summary_file = os.path.join(os.path.dirname(__file__), "latest_summary.md")
        try:
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary_content)
            print(f"摘要已保存到: {summary_file}")
            
            # 可选：自动打开文件
            # os.startfile(summary_file)
        except Exception as e:
            print(f"保存摘要失败: {e}")

        return summary_content

    except Exception as e:
        print(f"调用火山引擎API失败：{e}")
        return None
    finally:
        # 清理代理环境变量
        if 'HTTP_PROXY' in os.environ:
            del os.environ['HTTP_PROXY']
            del os.environ['HTTPS_PROXY']

async def generate_news_summary_chunked(start_date: str, end_date: str, fetch_news_with_content, VOLCENGINE_API_KEY):
    """
    生成新闻摘要（分块处理版本，用于处理大量内容）
    """
    processed_news = fetch_news_with_content(start_date, end_date)
    if not processed_news:
        print("没有找到包含正文内容的新闻。")
        return None

    print(f"成功读取 {len(processed_news)} 条新闻内容。")
    print("使用分块处理方式构建大模型API的Prompt...")
    
    # 将新闻数据分成较小的块
    chunk_size = 25  # 每块处理25条新闻
    chunks = [processed_news[i:i + chunk_size] for i in range(0, len(processed_news), chunk_size)]
    
    summaries = []
    
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=VOLCENGINE_API_KEY,
    )
    
    for i, chunk in enumerate(chunks):
        # 为每个块生成内容
        chunk_content = "\n\n-----\n\n".join([
            f"标题: {n['title']}\n"
            f"真实链接: {n['real_url']}\n"
            f"正文: {n['content']}" 
            for n in chunk
        ])
        print(f"处理第 {i+1}/{len(chunks)} 块内容（{my_utils.string_to_bytes(chunk_content)}KB）...")
        
        prompt_text = f"""你是一名资深的新闻编辑，请对以下BTC和加密货币新闻进行分析和总结（第{i+1}部分，共{len(chunks)}部分）：

        要求：
        1. 以markdown格式输出
        2. 将新闻进行主题聚类，每个聚类需要一个简洁的主题标题（用###开头）
        3. 总结每个聚类的主旨，风格要求公正、客观、简洁（用 **总结** 开头）
        4. 在每个聚类下，用无序列表列出原始新闻的标题和链接（用 **参考** 开头）

        以下是新闻内容：

        -----

        {chunk_content}
        """
        
        try:
            response = client.chat.completions.create(
                model=DOUBAO_MODEL_FLASH,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.3,
            )
            
            chunk_summary = response.choices[0].message.content
            summaries.append(chunk_summary)
            print(f"第 {i+1} 块处理完成")
            
        except Exception as e:
            print(f"处理第 {i+1} 块时出错: {e}")
            continue
    
    # 合并所有摘要
    if summaries:
        print("合并所有分块摘要...")
        final_prompt = f"""你是一名资深的新闻编辑，请将以下分块摘要合并成一份完整的BTC和加密货币市场周报：

        {"".join([f"=== 第{i+1}部分摘要 ===\n{summary}\n\n" for i, summary in enumerate(summaries)])}

        要求：
        1. 全文以markdown格式输出
		2. 结构为：
        2. 将所有内容重新整理和聚类，每个聚类的标题用 ###开头：内容包括
            - **总结**：用有序列表呈现聚类后的主旨
            - **参考**：用无序列表列出相关新闻标题和链接，格式为[标题](url)
        3. 将上述聚类的内容（标题、总结、参考），基于标题，归类到下述的一级主题中：
            # 各国政策与监管变化
            # 企业与机构的活动
            # 价格波动与市场风险
            # 其它相关事件
		4. 最终全文的输出结构为：
			# 各国政策与监管变化
			    ### 聚类标题
			        **总结**
			        **参考**
			    ### 聚类标题
			        **总结**
			        **参考**
            # 企业与机构的活动
			    （同上结构）
            # 价格波动与市场风险
			    （同上结构）
            # 其它相关事件
			    （同上结构）
        """
        if LOCAL_DEV:
            my_utils.copy_to_clipboard(final_prompt)
        
        try:
            response = client.chat.completions.create(
                model=DOUBAO_MODEL_THINKING,
                messages=[{"role": "user", "content": final_prompt}],
                temperature=0.3,
            )
            
            # 提取最终摘要
            final_summary = response.choices[0].message.content
            
            # 保存最终摘要
            summary_file = os.path.join(os.path.dirname(__file__), "latest_summary.md")
            try:
                with open(summary_file, "w", encoding="utf-8") as f:
                    f.write(final_summary)
                print(f"最终摘要已保存到: {summary_file}")
            except Exception as e:
                print(f"保存摘要失败: {e}")
            
            # 同时保存合并前的分块摘要（用于调试）
            chunks_file = os.path.join(os.path.dirname(__file__), "latest_summary_chunks.md")
            try:
                with open(chunks_file, "w", encoding="utf-8") as f:
                    f.write("\n\n=== 分块摘要合集 ===\n\n")
                    for i, summary in enumerate(summaries):
                        f.write(f"## 第{i+1}部分摘要\n\n{summary}\n\n---\n\n")
                print(f"分块摘要已保存到: {chunks_file}")
            except Exception as e:
                print(f"保存分块摘要失败: {e}")
            
            return final_summary
            
        except Exception as e:
            print(f"生成最终摘要时出错: {e}")
            return None
    
    print("没有成功处理任何内容块")
    return None

def generate_title_and_summary_and_content(content=None, LOCAL_DEV=False):
    """
    从内容中提取标题和主体内容
    :param content: 新闻内容
    """
    if not content and LOCAL_DEV:
        # 尝试从本地文件读取内容
        summary_file = os.path.join(os.path.dirname(__file__), "latest_summary.md")
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"已从本地文件读取内容: {summary_file}")
        except Exception as e:
            print(f"读取本地文件失败: {e}")
            return None, None
    
    if not content:
        lark.logger.error("Markdown content is None")
        return None, None
    
    title, summary = generate_title_and_summary(content)
    if not title or not summary:
        print("错误：生成标题或摘要失败")
        return None, None
    
    # message_content = f"{summary}\n---\n{content}"
    return title, summary