# PKPM-CAE 叠合梁参数化建模项目 - 技术小结

## 一、项目概述

### 1.1 项目目标
开发一个基于 PyPCAE API 的叠合梁参数化建模工具，通过 Excel 输入参数，自动生成 PKPM-CAE 可执行的 Python 脚本，实现：
- 工字型截面叠合梁的几何建模（下翼缘 + 腹板 + 后浇层）
- 预应力孔道的 3D 贯通建模
- 纵向钢筋和箍筋的自动布置
- 钢筋嵌入混凝土的相互作用定义

### 1.2 技术栈
- **PyPCAE**: PKPM-CAE 的 Python 脚本建模 API
- **Python**: 核心逻辑实现
- **PyQt5**: 用户界面
- **openpyxl**: Excel 参数读取

### 1.3 项目路径
```
D:\工作\数字游民\接单\December\思媚建筑\阶段成果\pkpm_composite_beam_V3.2_FINAL\pkpm_composite_beam\
```

---

## 二、核心文件结构

```
pkpm_composite_beam/
├── main.py                 # 脚本生成器（核心！）
├── ui_main_pro.py          # PyQt5 用户界面
├── core/
│   ├── parameters.py       # 参数定义（GeometryParams, StirrupParams 等）
│   ├── rebar_engine.py     # 钢筋布置引擎（核心！）
│   └── excel_parser.py     # Excel 解析器
├── pkpm_composite_beam_model.py  # 生成的输出脚本
└── 参数输入模板.xlsx        # Excel 输入模板
```

### 2.1 关键文件说明

| 文件 | 职责 | 重要程度 |
|------|------|----------|
| `main.py` | 将参数转换为 PyPCAE 脚本代码 | ⭐⭐⭐⭐⭐ |
| `core/rebar_engine.py` | 计算钢筋节点和单元的坐标 | ⭐⭐⭐⭐⭐ |
| `core/parameters.py` | 定义所有参数的数据结构 | ⭐⭐⭐⭐ |
| `ui_main_pro.py` | 用户界面，调用 main.py | ⭐⭐⭐ |

---

## 三、工字型叠合梁几何结构

### 3.1 截面示意图（从梁端面看）

```
                    ← 250mm (Tw) →
              ┌─────────────────────┐  Z=800 (H)
              │                     │
              │     后浇层          │  Z=500~800
              │   (cast layer)      │
              ├─────────────────────┤  Z=500 (h_pre)
              │                     │
              │      腹板           │  Z=150~500
              │     (web)           │
              │                     │
    ┌─────────┼─────────────────────┼─────────┐  Z=150 (tf)
    │         │                     │         │
    │   下翼缘（翅膀）               │         │  Z=0~150
    │   (bottom flange)             │         │
    └─────────┴─────────────────────┴─────────┘  Z=0

    ←───────────── 650mm (flange_width) ─────────────→
         bf=200        Tw=250         bf=200
```

### 3.2 关键尺寸参数

| 参数名 | 含义 | 典型值 | Excel字段 |
|--------|------|--------|-----------|
| L | 梁总长 | 10000mm | geometry.L |
| H | 梁总高 | 800mm | geometry.H |
| Tw | 腹板宽度 | 250mm | geometry.Tw |
| bf_ll/bf_rl | 左/右下翼缘伸出宽度 | 200mm | geometry.bf_ll |
| tf_ll/tf_rl | 左/右下翼缘厚度 | 150mm | geometry.tf_ll |
| h_pre | 预制层高度 | 500mm | geometry.h_pre |

### 3.3 坐标系约定

- **X轴**: 梁的纵向（长度方向），0 ~ L
- **Y轴**: 梁的横向（宽度方向），以梁中心线为 0
- **Z轴**: 梁的竖向（高度方向），底面为 0

---

## 四、工字型箍筋设计（重点！）

### 4.1 箍筋形态

箍筋必须是**工字型**（外短内长），以适应工字型截面：

```
从梁端面看箍筋结构：

                ┌───────────┐           Z=H-cover (775mm)
                │           │
                │  内侧肢   │  Y=±100mm，贯通全高
                │  (长)     │
       ┌────────┤           ├────────┐  Z=tf-cover (125mm)
       │ 外侧肢 │           │ 外侧肢 │
       │ (短)   │           │ (短)   │  Y=±300mm，只在翼缘内
       └────────┴───────────┴────────┘  Z=cover (25mm)
        Y=-300  Y=-100   Y=+100  Y=+300
```

### 4.2 箍筋关键参数

| 参数 | 计算公式 | 示例值 |
|------|----------|--------|
| y_outer | flange_width/2 - cover | 300mm |
| y_inner | Tw/2 - cover | 100mm |
| z_bottom | cover | 25mm |
| z_flange_top_left | tf_ll - cover | 125mm |
| z_flange_top_right | tf_rl - cover | 125mm |
| z_top | H - cover | 775mm |

### 4.3 箍筋生成流程

```
create_stirrups()
    ├── 计算 y_outer, y_inner, z坐标
    ├── _create_i_shaped_stirrup_zone() [左加密区]
    ├── _create_i_shaped_stirrup_zone() [右加密区]
    └── _create_i_shaped_stirrup_zone() [非加密区]
            └── _create_single_i_shaped_stirrup() [单个箍筋]
                    ├── 创建10个关键节点
                    └── 创建10条边（Line）
```

---

## 五、PyPCAE API 要点

### 5.1 模型类型选择

| 模型类型 | 用途 | 线元素创建方式 |
|----------|------|----------------|
| FemModel | 有限元分析 | Element(nids=[...], type=ElementType.Link) |
| StruModel | 结构建模 | **Line(start, end, sid=...)** |

**本项目使用 StruModel**，所以钢筋必须用 `Line` 而不是 `Element`！

### 5.2 常用 PyPCAE 类

```python
from pypcae.enums import *
from pypcae.comp import *
from pypcae.stru import StruModel

# 材料
mat = Material("名称", iType=MaterialType.Concrete, E0=32500.0, poisson=0.2)

# 截面
sec = Section("名称", SectionType.Line, Circle(mat.id, 直径))

# 节点
n = Node(x, y, z)

# 线构件（钢筋）
line = Line(n1.id, n2.id, sid=sec.id)

# 面
surf = Surf([line1.id, line2.id, ...])

# 体
solid = Solid([surf1.id, surf2.id, ...])

# 嵌入（钢筋嵌入混凝土）
Embeded(tarElems=[solid.id], srcElems=rebar_ids, type=EmbededType.NodeToElem)
```

### 5.3 API 文档位置

```
D:\工作\数字游民\接单\December\思媚建筑\Demond\README.md
```

---

## 六、遇到的坑和解决方案

### 坑1: Rebar 类不存在

**问题**: 最初尝试使用 `Rebar.create_line()` 创建钢筋，报错 `NameError: name 'Rebar' is not defined`

**原因**: PyPCAE 中没有 Rebar 类

**解决**: 使用 `Node` + `Line` 组合创建钢筋
```python
n1 = Node(x1, y1, z1)
n2 = Node(x2, y2, z2)
line = Line(n1.id, n2.id, sid=sec_rebar.id)
```

---

### 坑2: Element vs Line

**问题**: 使用 `Element(nids=[...], type=ElementType.Link)` 创建钢筋，只显示节点不显示线

**原因**: StruModel 使用 `Line`，FemModel 使用 `Element`

**解决**: 改用 `Line(start, end, sid=...)`

---

### 坑3: 底筋 Z 坐标错误

**问题**: 底部受拉主筋放在 Z=175mm（腹板内），而不是 Z=25mm（翼缘内）

**原因**: 错误理解结构，以为底筋在腹板底部

**解决**: 底筋必须在**下翼缘**内，Z = cover（约25~30mm）
```python
z_bottom = cover  # 不是 tf + cover！
```

---

### 坑4: 箍筋宽度不足

**问题**: 箍筋只有腹板宽度（250mm），无法勾住翼缘边缘的底部主筋

**原因**: 箍筋按矩形设计，没有考虑工字型截面

**解决**: 设计**工字型箍筋**
- 外侧短肢 Y=±300mm（翼缘边缘）
- 内侧长肢 Y=±100mm（腹板边缘）

---

### 坑5: 默认值不一致

**问题**: `main.py` 中 bf 默认值是 200mm，但 `rebar_engine.py` 中默认值是 0，导致箍筋 Y 坐标只有 ±100mm

**原因**: 两处代码的默认值不同步

**解决**: 统一设置默认值
```python
bf = max(self.geometry.bf_ll, self.geometry.bf_rl, 200.0)  # 默认200mm
```

---

### 坑6: 翼缘厚度为0

**问题**: Excel 中翼缘厚度设为0，导致外侧短肢高度只有 50mm，几乎看不到

**原因**: 用户 Excel 数据不完整

**解决**:
1. 添加默认值保护：`tf = max(tf_ll, tf_rl, 100.0)`
2. 提醒用户在 Excel 中设置正确的翼缘厚度

---

### 坑7: 箍筋"看不到"外侧肢

**问题**: 用户说从截面看只有4个点在腹板宽度内，看不到"凸"字形

**原因**: 外侧短肢只存在于 Z=25~125mm（翼缘区域），在腹板区域（Z>150mm）确实只有内侧肢

**这是正确行为！** 需要在翼缘区域的截面才能看到"凸"字形。

---

## 七、调试技巧

### 7.1 清除缓存

每次修改 `rebar_engine.py` 后，必须删除 `__pycache__` 文件夹：
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### 7.2 验证箍筋坐标

在 `main.py` 的 `export_script()` 中有验证代码：
```python
print(f">>> 【验证】箍筋Y坐标范围: {min(y_coords):.1f} ~ {max(y_coords):.1f} mm")
```

期望输出：`箍筋Y坐标范围: -300.0 ~ 300.0 mm`

### 7.3 检查生成的脚本

```bash
# 检查 Y 坐标分布
grep -oE "Node\([^)]+\)" pkpm_composite_beam_model.py | cut -d',' -f2 | sort | uniq -c

# 检查特定位置的箍筋结构
grep "Node(25.00," pkpm_composite_beam_model.py
```

---

## 八、当前状态

### 8.1 已完成功能

- [x] 工字型截面几何建模（翼缘 + 腹板 + 后浇层）
- [x] 3D 贯通预应力孔道
- [x] 纵向钢筋布置（顶筋、底筋）
- [x] 工字型箍筋布置（外短内长）
- [x] 自适应 Z 高度（左右翼缘厚度可不同）
- [x] 钢筋嵌入混凝土（Embeded）
- [x] 预应力施加

### 8.2 待验证/优化

- [ ] 用户确认在翼缘区域截面能看到"凸"字形箍筋
- [ ] Excel 参数完整性校验
- [ ] 更多截面类型支持

---

## 九、快速上手

### 9.1 运行项目

```bash
cd D:\工作\数字游民\接单\December\思媚建筑\阶段成果\pkpm_composite_beam_V3.2_FINAL\pkpm_composite_beam
python ui_main_pro.py
```

### 9.2 修改箍筋逻辑

关键函数在 `core/rebar_engine.py`:
- `create_stirrups()`: 箍筋主入口
- `_create_single_i_shaped_stirrup()`: 单个工字型箍筋的节点和边

### 9.3 修改脚本输出

关键函数在 `main.py`:
- `export_script()`: 生成 PyPCAE 脚本的主函数

---

## 十、联系方式

如有问题，请联系项目负责人或查阅：
- PyPCAE 官方文档：`Demond/README.md`
- PKPM-CAE 软件内置帮助

---

*文档更新日期: 2026-01-06*
