# Decon Textbook - Bookmark Extraction & PDF Repair Feature

## 功能概述

为Decon Textbook添加了两个重大优化：

1. **书签优先提取** - 对于有嵌入式书签的PDF，跳过AI分析，直接提取章节结构
2. **PDF引用修复** - 在分割前修复PDF对象引用，防止出现数千个repair警告

## 工作流程

```
用户点击Decon Textbook
    ↓
Step 1: 加载PDF
    ↓
Step 2: 尝试提取书签
    ↓
    ├─ 有书签 & 连续（Chapter 1-N）？
    │   ├─ ✅ YES → 提取章节信息
    │   │   ↓
    │   │   修复PDF引用（pikepdf）
    │   │   ↓
    │   │   ⚡ 跳过AI分析
    │   │   ↓
    │   │   直接进入Step 6（分割）
    │   │
    │   └─ ❌ NO → 回退到AI分析
    │       ↓
    │       原有流程：TOC提取 + Gemini分析
    │       ↓
    │       Step 6（分割）
```

## 书签提取规则

### 连续性验证

只接受满足以下条件的书签：

1. ✅ 必须从 Chapter 1 开始
2. ✅ 章节号必须连续（1, 2, 3, ...）
3. ✅ 格式：`Chapter N: Title`
4. ❌ 任何不连续 → 立即停止，回退到AI

### 示例

**✅ 有效书签（会使用）**
```
Chapter 1: Introduction
Chapter 2: Atoms and Molecules
Chapter 3: Chemical Reactions
...
Chapter 24: Organic Chemistry
```

**❌ 无效书签（会回退到AI）**
```
Chapter 2: Atoms and Molecules  ← 没有Chapter 1
Chapter 3: Chemical Reactions
...
```

或

```
Chapter 1: Introduction
Chapter 2: Atoms and Molecules
Chapter 5: Thermochemistry  ← 跳过了3和4
...
```

## PDF引用修复

### 问题

某些PDF（尤其是扫描版或转换版）有损坏的对象引用，在分割时会产生大量警告：

```
Object ID 8790,0 ref repaired
Object ID 8789,0 ref repaired
Object ID 8793,0 ref repaired
...
（可能数千条）
```

### 解决方案

使用 **pikepdf** 在分割前修复PDF：

```python
import pikepdf

with pikepdf.open(pdf_path) as pdf:
    pdf.save(repaired_path)  # Auto-repairs structure
```

### 效果

- ✅ 修复对象引用
- ✅ 消除repair警告
- ✅ 减小文件大小（移除冗余数据）
- ✅ 保持页数和内容完整

**实测（Chemistry PDF）：**
- 原始：106 MB, 1323 pages
- 修复后：78 MB, 1323 pages
- 分割时：0个ref警告（修复前有数千个）

## 新增文件

### `func/pdf_bookmark_extractor.py`

**函数：**

1. `extract_chapters_from_bookmarks(pdf_path, total_pages)`
   - 提取并验证PDF书签
   - 返回章节列表或None

2. `repair_pdf_references(pdf_path, console=None)`
   - 修复PDF对象引用
   - 返回修复后的临时文件路径

3. `format_bookmark_chapters(chapters)`
   - 格式化章节信息用于console输出

## 修改文件

### `gui/qt.py`

**Step 2 改动（第737-783行）：**

```python
# PRIORITY: Try bookmark extraction first
all_chapters = extract_chapters_from_bookmarks(file_path, total_pages)

if all_chapters:
    # SUCCESS: Found valid bookmarks
    console.append("✓ Found valid chapter bookmarks")
    console.append(format_bookmark_chapters(all_chapters))
    console.append("\n⚡ Skipping AI analysis - using bookmark data")

    # CRITICAL: Repair PDF references
    repaired_pdf_path = repair_pdf_references(file_path, console)

    # Use repaired PDF for splitting
    if repaired_pdf_path != file_path:
        reader = PdfReader(repaired_pdf_path)
        pdf_to_split = repaired_pdf_path
    else:
        pdf_to_split = file_path

else:
    # FALLBACK: No bookmarks, use AI analysis
    console.append("! No valid bookmarks found - falling back to AI analysis")
    pdf_to_split = file_path
    # ... original TOC extraction code
```

**Step 7 改动（第964行）：**

```python
# Use repaired PDF if available (bookmark path), otherwise original (AI path)
created_files = split_pdf_by_chapters(pdf_to_split, all_chapters, decon_dir)
```

**Cleanup改动（第970-989行）：**

```python
# Cleanup: Remove temporary repaired PDF
if repaired_pdf_path and repaired_pdf_path != file_path:
    try:
        os.unlink(repaired_pdf_path)
        console.append("✓ Cleaned up temporary repaired PDF")
    except:
        pass
```

## 性能提升

### 有书签的PDF（如Chemistry教材）

**之前：**
- Step 2: 提取200页 (~5s)
- Step 3-5: AI分析TOC + 剩余页 (~30-60s)
- Step 6-7: 分割 + 数千个ref警告 (~20s)
- **总计：~55-85秒**

**现在：**
- Step 2: 提取书签 (~0.1s)
- Step 2.5: 修复PDF (~15s)
- Step 6-7: 分割，0个警告 (~10s)
- **总计：~25秒**

**节省：~60%时间 + 不消耗AI tokens**

### 无书签的PDF

流程不变，回退到原有AI分析

## 测试

### 测试脚本

1. `getPdfBookmarks.py` - 原始书签提取测试
2. `test_bookmark_integration.py` - 书签提取集成测试
3. `test_pdf_repair.py` - PDF修复测试
4. `test_split_repaired.py` - 修复后分割测试

### 测试结果

✅ **书签提取**
- Chemistry PDF: 24章连续提取
- 页码范围无缝衔接（48-90, 91-135, ...）
- 最后章节正确结束于1323页

✅ **PDF修复**
- pikepdf成功修复
- 106MB → 78MB
- 1323页保持完整
- 0个ref警告

## 依赖

- `PyPDF2` - PDF读取和分割
- `pikepdf>=9.0.0` - PDF修复（已在requirements.txt）

## 未来优化

1. 支持更多书签格式（目前只支持"Chapter N: Title"）
2. 对AI路径也添加PDF修复（目前只在书签路径修复）
3. 缓存修复后的PDF（避免重复修复同一文件）

---

**实现日期：** 2025-10-14
**测试状态：** ✅ 全部通过
