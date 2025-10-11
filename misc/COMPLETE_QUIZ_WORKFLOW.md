# 完整测验自动化工作流程

## 🎯 完美解决图片题目问题

本方案通过 **独立脚本生成带标注的 HTML/PDF** 来彻底解决图片题无法识别的问题。

## 📋 完整流程

### 阶段 1: 生成带标注的题目文件

```bash
cd func
python annotate_quiz_pdf.py
```

**输出:**
- ✅ `quiz_res/quiz_with_questions.html` - 带醒目题号标注的 HTML
- ✅ (可选) `quiz_res/quiz_annotated.pdf` - PDF 版本

**效果:**
每个题目上方会有红色醒目标注:
```
┌─────────────────────────────────────────────────────────┐
│  题目 13  Question 13                                   │
│  ID: question_97585590                                  │
│  Which electron configuration represents a violation... │
│  共 6 个选项                                             │
└─────────────────────────────────────────────────────────┘
```

### 阶段 2: 打开并查看标注文件

**方法 A: 双击批处理文件**
```bash
func/open_quiz_html.bat
```

**方法 B: 手动在浏览器打开**
```
file:///C:/Users/mc282/Downloads/niubiaaaa/quiz_res/quiz_with_questions.html
```

**方法 C: 如果安装了 PDF 工具,直接打开 PDF**
```
quiz_res/quiz_annotated.pdf
```

### 阶段 3: 运行自动答题脚本

```bash
cd func
python getQuiz.py
```

**工作流程:**

1. **AI 自动答题** (27/31 题)
   ```
   Successfully received answers from Gemini.
   ```

2. **发现未回答题目** (4 题 - 图片题)
   ```
   ⚠️  发现 4 个未回答的题目
   Found 4 unanswered questions

   可能原因:
   - 题目或选项包含图片 (Images in question/answers)

   是否手动输入这些题目的答案? / Manually input answers?
   输入 'y' 或 'yes' 进入手动输入模式
   >
   ```

3. **输入 `y` 进入手动输入模式**

4. **对照 HTML/PDF 输入答案**
   ```
   ============================================================
   手动输入答案 / Manual Answer Input
   ============================================================

   ------------------------------------------------------------
   题目 ID: question_97585590
   问题: Which electron configuration represents a violation of the P...

   可选答案:
     1. ID: 4690 - [图片选项 / Image option]
     2. ID: 201 - [图片选项 / Image option]
     3. ID: 2627 - [图片选项 / Image option]
     4. ID: 9231 - [图片选项 / Image option]
     5. ID: 2631 - [图片选项 / Image option]

   请输入答案ID或选项编号 (或 skip/quit):
   ```

5. **查看 HTML 找到 "题目 13"**
   - HTML 中会显示完整的图片选项
   - 根据图片选择正确答案
   - 假设正确答案是第 3 个图片

6. **输入选项编号**
   ```
   > 3
   ✓ 已设置答案: 2627
   ```

7. **重复直到所有图片题都回答**

8. **答案确认**
   ```
   ============================================================
   答案检查 / Answer Review
   ============================================================

   总题数 / Total Questions: 31
   已回答 / Answered: 31
   未回答 / Unanswered: 0

   ✓ 所有题目已回答 / All questions answered
   是否提交? / Submit now?
   > y
   ```

9. **提交成功**
   ```
   ✅ Quiz submitted successfully!
   ```

## 🎨 HTML 标注特性

### 醒目标注样式
- 🔴 **红色背景** - 极其醒目
- 📝 **大号题号** - "题目 13" 32px 字体
- 🆔 **题目 ID** - 黄色显示完整 ID
- 📄 **问题预览** - 显示前 100 字符
- 🔢 **选项数量** - 提示有多少个选项

### 浏览器功能
- `Ctrl+F` 搜索题号 (如: "题目 13")
- `Ctrl+P` 打印为 PDF 保存
- 鼠标滚轮快速定位题目
- 缩放查看图片细节

## 📁 文件结构

```
niubiaaaa/
├── func/
│   ├── annotate_quiz_pdf.py       # 独立标注脚本
│   ├── getQuiz.py                 # 主答题脚本
│   ├── open_quiz_html.bat         # 快速打开 HTML
│   ├── setup_pdf_tools.bat        # PDF 工具安装
│   ├── PDF_ANNOTATION_GUIDE.md    # 标注工具指南
│   └── QUIZ_USAGE.md              # 答题脚本指南
│
├── quiz_res/
│   ├── quiz_with_questions.html   # ⭐ 带标注的 HTML
│   ├── quiz_annotated.pdf         # (可选) 带标注的 PDF
│   └── questions.md               # 题目列表
│
└── COMPLETE_QUIZ_WORKFLOW.md      # 本文件
```

## 💡 最佳实践

### 推荐工作流

1. **第一次做测验前:**
   ```bash
   # 生成标注文件(只需运行一次)
   python func/annotate_quiz_pdf.py
   ```

2. **每次做测验时:**
   ```bash
   # 打开 HTML 查看
   func/open_quiz_html.bat

   # 运行答题脚本
   cd func && python getQuiz.py
   ```

3. **遇到图片题时:**
   - 在浏览器中 `Ctrl+F` 搜索题号
   - 查看图片选择答案
   - 在终端输入选项编号

### 提高效率的技巧

1. **双屏使用**
   - 一个屏幕显示 HTML
   - 另一个屏幕运行脚本

2. **快捷键**
   - `Ctrl+F` 快速搜索题号
   - `Alt+Tab` 快速切换窗口
   - `Tab` 键在终端选择历史输入

3. **批量输入**
   - 先浏览所有图片题
   - 记下答案编号
   - 连续快速输入

## 🔧 故障排除

### Q: HTML 文件打不开?
**A:**
```bash
# 检查文件是否存在
dir quiz_res\quiz_with_questions.html

# 手动用浏览器打开
# 右键 -> 打开方式 -> Chrome/Edge
```

### Q: 图片不显示?
**A:**
- HTML 中的图片是 Canvas 服务器的链接
- 需要保持网络连接
- 或者使用浏览器的 "另存为" 保存完整网页

### Q: 题号对不上?
**A:**
- 脚本按顺序编号 (1-31)
- 对应 question_97585578 = Q1, question_97585590 = Q13
- 终端会显示完整 ID

### Q: 想要 PDF 而不是 HTML?
**A:**
```bash
# 安装 PDF 工具 (三选一)
pip install weasyprint          # 最简单
pip install pdfkit              # 需要 wkhtmltopdf
pip install playwright          # 最可靠

# 重新运行脚本
python func/annotate_quiz_pdf.py
```

## 📊 对比不同方案

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **HTML 标注** (当前) | ✅ 无需额外工具<br>✅ 可搜索<br>✅ 图片完整 | ❌ 需要网络 | ⭐⭐⭐⭐⭐ |
| PDF 标注 | ✅ 离线使用<br>✅ 便于打印 | ❌ 需要工具<br>❌ 不可搜索 | ⭐⭐⭐⭐ |
| 直接查看 Canvas | ✅ 原始页面 | ❌ 无标注<br>❌ 难以定位 | ⭐⭐ |
| 下载原始 PDF | ✅ 官方文档 | ❌ 题号不对应 | ⭐⭐⭐ |

## 🎉 总结

这个完整方案的优势:

1. **彻底解决图片题问题** - 通过独立脚本生成可视化文件
2. **不影响主逻辑** - 标注脚本和答题脚本独立
3. **灵活可调整** - 可以修改标注样式、输出格式
4. **易于调试** - 每个步骤都有清晰输出
5. **用户友好** - 双语提示、醒目标注、便捷操作

**关键创新点:**
- ✅ 独立脚本设计 - 可以反复试错
- ✅ 醒目视觉标注 - 红色背景 + 大号字体
- ✅ 灵活输入方式 - 支持编号/ID/跳过
- ✅ 双重确认机制 - 防止误提交
- ✅ 完整文档支持 - 三份指南覆盖所有场景

你现在拥有了一个**健壮、灵活、易用**的测验自动化系统! 🚀
