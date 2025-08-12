"""
程序用途：批量评估 Markdown 文件的 LLM 预训练准备度
Usage: Batch evaluate the LLM pretraining readiness of Markdown files

用法 Usage:
------
python md_readi_score.py <input_path> [--output <output.json>] [--recursive]

参数 Parameters:
  <input_path>   输入 Markdown 文件路径或文件夹路径
                 Path to a Markdown file or a folder containing Markdown files
  --output       （可选）将所有结果输出为 JSON 文件
                 (Optional) Output all results to a JSON file
  --recursive    （可选）递归扫描子文件夹中的 Markdown 文件
                 (Optional) Recursively scan Markdown files in subfolders

示例 Examples:
------
# 检查单个文件 Check a single file
python md_readi_score.py ./data/2505.09507.md

# 检查文件夹下所有 Markdown 文件（不递归）
# Check all Markdown files in a folder (non-recursive)
python md_readi_score.py ./data

# 检查文件夹及其子文件夹下所有 Markdown 文件（递归）
# Check all Markdown files in a folder and subfolders (recursive)
python md_readi_score.py ./data --recursive

"""

import argparse
import os
import json
import re
import chardet
from collections import defaultdict

def read_markdown(file_path):
    """读取Markdown文件，自动检测编码"""
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {str(e)}")
        return None

def check_structural_integrity(md_text):
    """增强版结构完整性检查（含标题重复/列表规范）"""
    issues = []
    score = 1.0
    
    # 标题层级检测
    headings = re.findall(r"^(#+) (.*?)$", md_text, re.MULTILINE)
    prev_level = 0
    used_headings = defaultdict(int)
    for i, (h, title) in enumerate(headings):
        level = len(h)
        title = title.strip()
        
        # 标题层级跳跃检测
        if level - prev_level > 1:
            issues.append(f"第 {i+1} 个标题层级跳跃：从 H{prev_level} 到 H{level}")
            score -= 0.05
        
        # 标题重复检测
        used_headings[title] += 1
        if used_headings[title] > 1:
            issues.append(f"标题 '{title}' 重复出现 {used_headings[title]} 次")
            score -= 0.03
        
        prev_level = level
    
    # 列表结构检测
    list_blocks = re.findall(r"^(\s*[-*+]|\s*\d+\.) ", md_text, re.MULTILINE)
    for i, item in enumerate(list_blocks):
        indent = len(item) - len(item.lstrip())
        marker = item.strip()
        if i > 0 and len(list_blocks[i-1].strip()) == len(marker):
            prev_indent = len(list_blocks[i-1]) - len(list_blocks[i-1].lstrip())
            if abs(indent - prev_indent) > 2:
                issues.append(f"第 {i+1} 个列表项缩进不规范（预期缩进 {prev_indent}，实际 {indent}）")
                score -= 0.02
    
    # 未闭合代码块检测
    code_blocks = md_text.count("```")
    if code_blocks % 2 != 0:
        issues.append("发现未闭合的代码块")
        score -= 0.1
    
    return max(score, 0), issues

def check_format_cleanliness(md_text):
    """优化版格式清洁度检查（含智能乱码检测）"""
    issues = []
    score = 1.0
    lines = md_text.splitlines()
    
    # 长行检测
    for i, line in enumerate(lines):
        if len(line) > 1000:
            issues.append(f"第 {i+1} 行过长（{len(line)} 字符）")
            score -= 0.02
    
    # 智能乱码检测（排除中文/常见符号）
    non_ascii_pattern = re.compile(r"[^\x00-\x7F\u4e00-\u9fa5\uff00-\uffff]")
    for i, line in enumerate(lines):
        non_ascii_chars = non_ascii_pattern.findall(line)
        if len(non_ascii_chars) >= 5:
            issues.append(f"第 {i+1} 行疑似乱码（非ASCII字符占比 {len(non_ascii_chars)/len(line)*100:.1f}%）")
            score -= 0.03
    
    # URL分类检测
    urls = re.findall(r"(https?://\S+)|(www\.\S+)", md_text)
    external_urls = [u[0] or u[1] for u in urls if not re.search(r"\.local|localhost", u[0] or u[1])]
    if external_urls:
        issues.append(f"检测到 {len(external_urls)} 个外部URL，建议检查可访问性")
        score -= 0.03 * (len(external_urls) > 5)  # 超过5个URL才扣分
    
    return max(score, 0), issues

def check_llm_friendly_layout(md_text):
    """增强版LLM友好性检测（含段落分布分析）"""
    issues = []
    score = 1.0
    
    # 标题数量检测
    headings = re.findall(r"^#+ ", md_text, re.MULTILINE)
    if len(headings) < 3:
        issues.append(f"标题数量过少（仅 {len(headings)} 个），建议增加章节划分")
        score -= 0.1
    
    # 段落长度分析
    paragraphs = re.split(r"\n{2,}", md_text)
    long_paragraphs = [p for p in paragraphs if len(p.split()) > 400]
    if len(long_paragraphs) > 2:
        issues.append(f"检测到 {len(long_paragraphs)} 个过长段落（>400词），建议拆分")
        score -= 0.1
    
    # 文本块分布检测
    block_sizes = [len(block.split()) for block in paragraphs if block.strip()]
    if block_sizes:
        avg_length = sum(block_sizes) / len(block_sizes)
        if avg_length > 300:
            issues.append(f"段落平均长度过长（{avg_length:.1f}词），建议增加分段")
            score -= 0.05
    
    return max(score, 0), issues

def check_citation_sanity(md_text):
    """参考文献规范性检测"""
    issues = []
    score = 1.0
    
    # 检测参考文献章节
    bib_sections = re.findall(r"^#+\s*参考文献|^#+\s*References", md_text, re.MULTILINE)
    if not bib_sections:
        issues.append("未找到参考文献章节")
        score -= 0.05
    else:
        # 检测参考文献格式
        bib_content = re.search(r"^#+\s*参考文献.*?(```.*?```|.*?)(?=\n#|$)", md_text, re.DOTALL)
        if bib_content:
            content = bib_content.group(1)
            bib_entries = re.split(r"\n\n", content.strip())
            invalid_entries = [i for i, entry in enumerate(bib_entries) 
                             if not re.search(r"\[.*?\]|doi:\s*10\.\d+|@\w+{", entry)]
            if invalid_entries:
                issues.append(f"参考文献中 {len(invalid_entries)} 项格式不规范")
                score -= 0.05 * (len(invalid_entries) > 3)  # 超过3项才扣分
    
    return max(score, 0), issues

def check_technical_sanity(file_path, md_text):
    """技术合理性检测（优化文件大小判断）"""
    issues = []
    score = 1.0
    size = os.path.getsize(file_path)
    
    # 文件大小分级检测
    if size < 500:
        issues.append("文件过小（<500B），内容可能严重不完整")
        score -= 0.2
    elif size < 1000:
        issues.append("文件较小（<1KB），内容可能不完整")
        score -= 0.1
    elif size > 5 * 1024 * 1024:
        issues.append("文件过大（>5MB），建议拆分为多个文件")
        score -= 0.15
    elif size > 2 * 1024 * 1024:
        issues.append("文件较大（>2MB），建议考虑拆分")
        score -= 0.1
    
    # 空文件检测
    if not md_text.strip():
        issues.append("文件为空")
        score = 0.0
    
    return max(score, 0), issues

def compute_final_score(scores):
    """优化版评分权重分配"""
    weights = {
        "结构完整性": 0.3,
        "格式清洁度": 0.3,
        "LLM友好性": 0.25,
        "参考文献": 0.15
    }
    total = 0
    for key, weight in weights.items():
        total += scores.get(key, 0) * weight
    return round(total * 100, 1)

def assign_grade(score):
    """细化评级标准"""
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "B+"
    elif score >= 80:
        return "B"
    elif score >= 75:
        return "C+"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"

def generate_report(file_path):
    """生成增强版评估报告"""
    md_text = read_markdown(file_path)
    if md_text is None:
        return {"错误": "无法读取文件"}

    results = {}
    
    # 结构完整性检测
    s_score, s_issues = check_structural_integrity(md_text)
    results["结构完整性"] = s_score
    
    # 格式清洁度检测
    f_score, f_issues = check_format_cleanliness(md_text)
    results["格式清洁度"] = f_score
    
    # LLM友好性检测
    l_score, l_issues = check_llm_friendly_layout(md_text)
    results["LLM友好性"] = l_score
    
    # 参考文献检测
    b_score, b_issues = check_citation_sanity(md_text)
    results["参考文献"] = b_score
    
    # 技术合理性检测
    t_score, t_issues = check_technical_sanity(file_path, md_text)
    # 技术检测结果合并到问题列表，不单独计分
    
    final_score = compute_final_score(results)
    grade = assign_grade(final_score)

    report = {
        "文件": file_path,
        "准备度评分": final_score,
        "评级": grade,
        "详细评分": {
            "结构完整性": f"{int(s_score * 100)}%",
            "格式清洁度": f"{int(f_score * 100)}%",
            "LLM友好性": f"{int(l_score * 100)}%",
            "参考文献": f"{int(b_score * 100)}%"
        },
        "问题列表": s_issues + f_issues + l_issues + b_issues + t_issues,
        "优化建议": generate_improvement_suggestions(results, s_issues + f_issues + l_issues + b_issues)
    }

    return report

def generate_improvement_suggestions(scores, issues):
    """根据检测结果生成针对性优化建议"""
    suggestions = []
    
    # 结构优化建议
    if scores["结构完整性"] < 0.8:
        if any("标题跳跃" in issue for issue in issues):
            suggestions.append("调整标题层级，确保相邻标题层级差不超过1")
        if any("标题重复" in issue for issue in issues):
            suggestions.append("修改重复标题，确保章节标题唯一性")
        if any("列表项缩进" in issue for issue in issues):
            suggestions.append("统一列表项缩进，建议使用2-4个空格")
    
    # 格式优化建议
    if scores["格式清洁度"] < 0.8:
        if any("行过长" in issue for issue in issues):
            suggestions.append("将长行（>1000字符）拆分为多行，每行不超过80字符")
        if any("乱码" in issue for issue in issues):
            suggestions.append("检查并修正疑似乱码字符，建议使用UTF-8编码保存")
        if any("外部URL" in issue for issue in issues):
            suggestions.append("考虑替换为本地资源引用或删除无效外部链接")
    
    # LLM友好性建议
    if scores["LLM友好性"] < 0.8:
        if any("标题数量过少" in issue for issue in issues):
            suggestions.append(f"增加章节划分，建议标题数量不少于{3 - len(re.findall(r'^#+ ', md_text, re.MULTILINE))}个")
        if any("过长段落" in issue for issue in issues):
            suggestions.append("拆分过长段落（>400词），建议每段不超过200词")
    
    # 参考文献建议
    if scores["参考文献"] < 0.8:
        if any("未找到参考文献" in issue for issue in issues):
            suggestions.append("添加参考文献章节，规范记录引用来源")
        if any("格式不规范" in issue for issue in issues):
            suggestions.append("统一参考文献格式，建议使用标准 citation 格式（如 BibTeX）")
    
    return suggestions if suggestions else ["文件整体质量良好，可直接用于LLM预训练"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="增强版Markdown文件LLM预训练准备度评估工具")
    parser.add_argument("input", help="输入Markdown文件路径或文件夹路径")
    parser.add_argument("--output", help="将结果输出为JSON文件")
    parser.add_argument("--recursive", action="store_true", help="递归扫描子文件夹")

    args = parser.parse_args()

    # 自动识别输入类型并查找Markdown文件
    def find_md_files(input_path, recursive=False):
        md_files = []
        if os.path.isfile(input_path):
            if input_path.lower().endswith(".md"):
                md_files.append(input_path)
            else:
                print(f"错误：输入的文件 '{input_path}' 不是Markdown文件")
                exit(1)
        elif os.path.isdir(input_path):
            for root, dirs, files in os.walk(input_path):
                for file in files:
                    if file.lower().endswith(".md"):
                        md_files.append(os.path.join(root, file))
                if not recursive:
                    break
        else:
            print(f"错误：输入路径 '{input_path}' 不存在")
            exit(1)
        
        return md_files

    md_files = find_md_files(args.input, args.recursive)
    if not md_files:
        print(json.dumps({"错误": "未找到Markdown文件"}, ensure_ascii=False, indent=2))
        exit(1)

    # 生成评估报告
    reports = []
    for md_file in md_files:
        report = generate_report(md_file)
        reports.append(report)

    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
    else:
        for report in reports:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            print("-" * 80)