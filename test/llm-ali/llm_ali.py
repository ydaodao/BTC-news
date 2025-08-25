import os
from openai import OpenAI

LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'

def generate_title_and_summary(content):
    client = OpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=os.getenv("ALI_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    prompt_text = f"""为以下新闻内容：
        1 输出一个markdown一级标题：格式为【加密货币周报：xxxxx】，其中xxxxx 替换为热点新闻的提炼；
        2 输出一段对这些热点新闻的简要总结：总数不超过200字，不同的总结内容请换行输出（用markdown无序列表格式）；
        3 主打客观真实，不要用花里胡哨的语言，也不要用过于活泼的风格。

        以下是新闻内容：

        -----
        
        {content}
        """

    completion = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model="qwen-plus-latest",
        messages=[
            # {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt_text},
        ]
    )
    # print(completion.model_dump_json())

    # 从返回结果中提取生成的文本
    generated_text = completion.choices[0].message.content
    if LOCAL_DEV:
        print("生成的文本:", generated_text)

        # 保存处理后的markdown内容到同级目录
        title_and_summary_path = os.path.join(os.path.dirname(__file__), "title_and_summary.md")
        try:
            with open(title_and_summary_path, 'w', encoding='utf-8') as f:
                f.write(generated_text)
            print(f"Title and summary saved to: {title_and_summary_path}")

        except Exception as e:
            print(f"Failed to save title and summary: {e}")

    # 从生成的文本中提取标题和总结
    lines = generated_text.split("\n")
    title = lines[0].replace("#", "").strip()
    summary = '\n'.join(lines[1:]).strip()

    return title, summary

if __name__ == "__main__":
    content = ""
    # 尝试从本地文件读取内容
    summary_file = os.path.join(os.path.dirname(__file__), "latest_summary.md")
    try:
        with open(summary_file, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"已从本地文件读取内容: {summary_file}")
    except Exception as e:
        print(f"读取本地文件失败: {e}")

    title, summary = generate_title_and_summary(content)
    print(title)
    print(summary)