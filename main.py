from Markdown_Spliter.markdown_parser import MarkdownParser
import os

if __name__ == '__main__':
    path = "Example_Articles"
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                print(f"Processing {file_path}...")
                parser = MarkdownParser.init_by_path(file_path)
                metadata = parser.get_metadata()
                parse_tree = parser.get_parse_tree()
                # 获取第一章的全部内容（包括所有子节、子条）
                chapter_content = parser.get_section_content(description="chapter", title="第一章")

                # 获取摘要部分
                abstract = parser.get_section_content(description="abstract_ch")

                # 获取特定级别的内容（例如所有节）
                sections = parser.get_section_content(level=2)

                # 通过精确标题查找
                specific_section = parser.get_section_content(exact_title="研究背景")