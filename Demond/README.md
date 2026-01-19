## 一、概览
### 1、简介
PyPCAE是PKPM-CAE软件集成的基于`Python`的脚本式建模功能。用户可基于该功能通过编写脚本的方法便捷高效地进行参数化建模。
执行基于PyPCAE编写的脚本后，将生成可被软件解析的包括节点、单元、边界条件等在内的模型数据，并可被软件可视化地展示。

## 二、使用
### 1、导入模块
进行参数化建模前，应首先导入编程过程中所需的模块(`module`)，以调用模块中定义的类、方法、变量。
在PyPCAE中，应首先按需导入`pypcae.enums`，`pypcae.comp`，`pypcae.fem`(或`pypcae.stru`)和`math`：

|  代码  |  含义  |
|  ----  | ----  |
| **`from pypcae.enums import *`**  | 导入`PyPCAE`中定义的枚举值 |
| **`from pypcae.comp import *`**  | 导入`PyPCAE`的`comp`模块 |
| **`from pypcae.fem import FemModel`**  | 若建立有限元模型，则导入`FemModel` |
| **`from pypcae.stru import StruModel`**  | 若建立结构模型，则导入`StruModel` |
| **`import math`**  | 如需进行数学运算，则导入`math`模块 |

### 2、建立有限元模型
#### 2.1、材料
> **`Material(name: str, iType: int, iModel: int, E0: float, poisson: float, density: float)`**

使用该类可创建固体力学材料。<br/>
`name`为材料名称，应传入字符串；<br/>
`iType`为材料类型，应使用`enums`中定义的[`MaterialType`](#materialtype)类，如`MaterialType.Concrete`；<br/>
`iModel`为本构类型，应使用`enums`中定义的[`MaterialModel`](#materialmodel)类，如`MaterialModel.Elastic`；<br/>
`E0`为弹性模量；<br/>
`poisson`为泊松比；<br/>
`density`为密度。<br/>
`Material`类可根据材料传入顺序依次为材料进行编号。<br/>
`Material`类已预先定义了形参`iType = MaterialType.Custom`，`iModel = MaterialModel.Elastic`，`E0 = 0.0`，`poisson = 0.0`与`density = 0.0`，故定义材料时应至少传入形参`name`。<br/>

#### 2.2、截面
> **`Section(name: str, type: int, sub: list[dict{"type": int, "params": list[float], "props": list[float], "mid": int}], iKey: int)`**

使用该类可创建截面。<br/>
`name`为截面名称，应传入字符串；<br/>
`type`为截面类型，应使用`enums`中定义的[`SectionType`](#sectiontype)类，如`SectionType.Solid`；<br/>
`sub`中，`"type"`为截面形状类型，应使用`enums`中定义的[`ShapeType`](#shapetype)类，如`ShapeType.SOLID`；`"params"`为截面参数；`"props"`为截面属性；`"mid"`为材料号；<br/>
`iKey`为截面属性传入方法，若`iKey`为`0`，表示直接给定截面属性；若`iKey`为`1`，表示传入参数计算截面属性。<br/>
`Section`类可根据截面传入顺序依次为截面进行编号。<br/>
`Section`类已预先定义了形参`type = SectionType.Solid`，`sub = None`与`iKey = 1`，故定义截面时应至少传入形参`name`。<br/>

<details>
<summary id="summary-1" style="color:red;">截面参数的定义方法(若 iKey = 0)</summary>

    - SOLID ,       实体截面: 使用 SolidSect(mid: int) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - RECTANGLE ,   矩形截面: 使用 Rectangle(mid: int, b: float, h: float) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - CIRCLE ,      圆形截面: 使用 Circle(mid: int, d: float) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - BOX ,         箱形截面: 使用 Box(mid: int, b: float, h: float, u: float, t: float, d: float, f: float) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - ISHAPE ,      工字形截面: 使用 IShape(mid: int, t: float, h: float, bu: float, tu: float, bd: float, td: float) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - CROSSING ,    十字形截面: 使用 Crossing(mid: int, b: float, h: float, u: float, t: float, d: float, f: float) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - TUBE ,        圆管形截面: 使用 Tube(mid: int, D: float, t: float) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - LSHAPE ,      L形截面: 使用 LShape(mid: int, b: float, h: float, d: float, f: float) 类. mid 为材料号, 其余参数含义可见 PKPM-CAE 截面部分. 该类未预先定义任何形参.
    - SINGLELAYER , 壳: 使用 SingleLayer(mid, t, offset, isotropy, normal) 类. 该类已预先定义了形参 offset = 0 , isotropy = 0 , 与 normal = None , 故定义时应至少传入形参 mid 与 t.
</details>
<details>
<summary id="summary-1" style="color:red">截面属性的定义方法(若 iKey = 1)</summary>

    - 使用 Arbitrary(mid: int, area: float, Ix: float, Iy: float, Iz: float, Iyz: float) 类. mid 为材料号, area 为截面面积, Ix 为截面对 x 轴的惯性矩, Iy 为截面对 y 轴的惯性矩, Iz 为截面对 z 轴的惯性矩, Iyz 为截面对 y, z 轴的惯性积. 该类已预先定义了形参 Ix = 0 , Iy = 0 , Iz = 0 与 Iyz = 0 , 故定义时应至少传入形参 mid 与 area.

</details>

**定义`mat`与`sec`时可只给定形参`name`的值，在操作PKPM-CAE的过程中可赋予`mat`与`sec`的其余特性。**

#### 2.3、节点
首先根据建模对象的几何特征与节点之间的相对关系，确定模型各个节点在三维直角坐标系中的坐标。<br/>
> **`Node(x: float, y: float, z: float)`**

使用该类可创建节点，将各个节点坐标分别传递到`Node`类中。<br/>
`x`为该节点`x`坐标的值；<br/>
`y`为该节点`y`坐标的值；<br/>
`z`为该节点`z`坐标的值。<br/>
`Node`类可根据节点传入顺序依次为节点进行编号。<br/>
`Node`类未预先定义任何形参，故定义节点时应至少传入形参`x`，`y`与`z`。<br/>

#### 2.4、单元
> **`Element(nids: list[int], type: int, sid: int, normal)`**

使用该类可创建单元<br/>
`nids`为该单元所包含的节点编号；<br/>
`type`为单元类型，应使用`enums`中定义的[`ElementType`](#elementtype)类，如`ElementType.BeamEuler`；<br/>
`sid`为与单元相对应的截面的编号。<br/>
`Element`类已预先定义了形参`type = ElementType.Link`，`sid = -1`与`normal = None`，故定义单元时应至少传入形参`nids`。<br/>

#### 2.5、集合
##### 2.5.1、节点集合
> **`Nset(name: str, ids: list[int])`**

使用该类可创建节点集合。<br/>
`name`为节点集合名称，应传入字符串；<br/>
`ids`为节点号。<br/>
`Nset`类已预先定义了形参`ids = None`，故定义节点集合时应至少传入形参`name`。<br/>

##### 2.5.2、单元集合
> **`Elset(name: str, ids: list[int])`**

使用该类可创建单元集合<br/>
`name`为单元集合名称，应传入字符串；<br/>
`ids`为单元号。<br/>
`Elset`类已预先定义形参`ids = None`，故定义单元集合时应至少传入形参`name`。<br/>

##### 2.5.3、接触单元
> **`Contactor(att: int, side=None: int, nids=None: list[int])`**

使用该类可创建接触单元，接触单元需要从属于接触面才能生效。<br/>
`att`为附着单元编号；<br/>
`side`为对应的附着单元表面号，对于面单元正向为1反向为2，对于四面体单元编号从1到4，对于六面体单元从1到6；<br/>
`nids`为接触单元节点号，当side缺省时nids用于确定side的值，对于面单元顺时针对应附着单元正向，体单元没有顺序要求。<br/>
`Contactor`类已预先定义了形参`side = None`和`nids = None`，故定义接触单元时应至少传入形参`att`, `side`和`nids`必填其一。<br/>

##### 2.5.4、接触面(接触单元集合)
> **`ContactSet(name: str, contactors: list[Contactor])`**

使用该类可创建接触面。<br/>
`name`为接触面名称，应传入字符串；<br/>
`contactors`为所包含的接触单元。<br/>
`ContactSet`类已预先定义了形参`contactors = None`，故定义接触面时应至少传入形参`name`。<br/>

#### 2.6、支座
##### 2.6.1、固定支座
> **`Fixed(gnids: list[int], dof: list[int], type: int)`**

使用该类可创建固定支座。<br/>
`gnids`为节点号；<br/>
`dof`为约束自由度；<br/>
`type`为约束类型，应使用`enums`中定义的[`FixedType`](#fixedtype)类，如`FixedType.Default`。<br/>
`Fixed`类已预先定义了全部形参，即：`gnids = None`，`dof = None`与`type = FixedType.Default`。<br/>

##### 2.6.2、弹性支座
> **`ElasSupport(gnids: list[int], type: int, kx: float, ky: float, kz: float, vx: list[float], vz: list[float])`**

使用该类可创建弹性支座。<br/>
`gnids`为节点号；<br/>
`type`为弹性支座类型，应使用`enums`中定义的[`ElasSupportType`](#elassupporttype)类，如`ElasSupportType.Lateral`；<br/>
`kx`，`ky`，`kz`为弹簧刚度系数，<br/>
`vx`为弹簧坐标系`x`轴方向余弦，<br/>
`vz`为弹簧坐标系`z`轴方向余弦。<br/>
`ElasSupport`类已预先定义了全部形参，即：`gnids = None`，`type = ElasSupportType.Lateral`，`kx = 0`，`ky = 0`，`kz = 0`，`vx = None`与`vz = None`。<br/>

##### 2.6.3、隔震支座
> **`IsolationBearing(gnids: list[int], type: int)`**

使用该类可创建隔震支座。<br/>
`gnids`为节点号；<br/>
`type`为隔震支座类型，应使用`enums`中定义的[`IsolationBearingType`](#isolationbearingtype)类，如`IsolationBearingType.General`。<br/>
`IsolationBearing`类已预先定义了全部形参，即：`gnids = None`与`type = IsolationBearingType.General`。<br/>

##### 2.6.4、主从约束
> **`DofSlave(slave: list[], master: list[list[]], coef: list[float])`**

使用该类可创建主从约束。<br/>
`slave`为自由度及对应源(从)节点号；<br/>
`master`为自由度及对应靶(主)节点号；<br/>
`coef`为从自由度方程系数。<br/>
`DofSlave`类已预先定义了全部形参，即：`slave = None`，`master = None`与`coef = None`。<br/>

##### 2.6.5、标准约束
> **`ConstrEqua(dofEqua: list[list[]], coef: list[float])`**

使用该类可创建标准约束。<br/>
`dofEqua`为自由度及对应节点号；<br/>
`coef`为常系数。<br/>
`ConstrEqua`类已预先定义了全部形参，即：`dofEqua = None`与`coef = None`。<br/>

#### 2.7、相互作用
##### 2.7.1、绑定
> **`Binding(tarNodes: list[int], srcNodes: list[int], type: int, iKey: int, iTol=1, tol: float)`**

使用该类可创建绑定相互作用。<br/>
`tarNodes`为靶(主)节点或节点集合号；<br/>
`srcNodes`为源(从)节点或节点集合号；<br/>
`type`为广义连接子类型(绑定类型)，应使用`enums`中定义的[`BindingType`](#bindingtype)类，如`BindingType.NodeToNode`；<br/>
`iKey`为自由度模式，应使用`enums`中定义的[`DofMode`](#dofmode)类，如`DofMode.Both`；<br/>
`iTol`为绑定容差模式，-1为强制绑定, 0为自动, 1为自定义；<br/>
`tol`为允许误差距离(绑定容差)，负值为内部自动确定。<br/>
`Binding`类已预先定义了全部形参，即：`tarNodes = None`，`srcNodes = None`，`type = BindingType.NodeToNode`，`iKey = DofMode.Both`与`tol = -1`。<br/>

##### 2.7.2、耦合
> **`Coupling(tarNode: int, srcNodes: list[int], type: int, iKey: int, iDofs: int)`**

使用该类可创建耦合相互作用。<br/>
`tarNode`为靶(主)节点号；<br/>
`srcNodes`为源(从)节点或节点集合号；<br/>
`type`为耦合类型，应使用`enums`中定义的[`CouplingType`](#couplingtype)类，如`CouplingType.Rigid`；<br/>
`iKey`为自由度模式，应使用`enums`中定义的[`DofMode`](#dofmode)类，如`DofMode.Both`；<br/>
`iDofs`为指定自由度。<br/>
`Coupling`类已预先定义了全部形参，即：`tarNodes = None`，`srcNodes = None`，`type = CouplingType.Rigid`，`iKey = DofMode.Both`与`iDofs = None`。<br/>

##### 2.7.3、嵌入
> **`Embeded(tarElems: list[int], srcElems: list[int], type: int, iKey: int, tol: float)`**

使用该类可创建嵌入相互作用。<br/>
`tarElems`为靶(主)单元或单元集合号；<br/>
`srcElems`为源(从)单元或单元集合号；<br/>
`type`为嵌入类型，应使用`enums`中定义的[`EmbededType`](#embededtype)类，如`EmbededType.NodeToElem`；<br/>
`iKey`为自由度模式，应使用`enums`中定义的[`DofMode`](#dofmode)类，如`DofMode.Both`；<br/>
`tol`为允许误差距离(嵌入容差)，暂时保留。<br/>
`Embeded`类已预先定义了全部形参，即：`tarElems = None`，`srcElems = None`，`type = EmbededType.NodeToElem`，`iKey = DofMode.Both`与`tol = -1`。<br/>

##### 2.7.4、接触对
> **`ContactPair(tarElems: list[int], srcElems: list[int], type: int, iMethod: int, penalty: float, slipTol: float, mu: float)`**

使用该类可创建接触对相互作用。<br/>
`tarElems`为靶(主)面接触面号；<br/>
`srcElems`为源(从)面接触面号；<br/>
`type`为接触类型，应使用`enums`中定义的[`ContactType`](#contacttype)类，如`ContactType.ElasToElas`；<br/>
`iMethod`为离散类型(接触计算方法)，应使用`enums`中定义的[`ContactMethod`](#contactmethod)类，如`ContactMethod.NodeToSurf`；<br/>
`penalty`为罚系数；<br/>
`slipTol`为作用间隙；<br/>
`mu`为摩擦系数。<br/>
`ContactPair`类已预先定义了全部形参，即：`tarElems = None`，`srcElems = None`，`type = ContactType.ElasToElas`，`iMethod = ContactMethod.NodeToSurf`，`penalty = -1`，`slipTol = 0`与`mu = 0`。<br/>

##### 2.7.5、连接器截面
> **`ConnectorSection(name: str, iType: int, keyStiff: int, consElas: float, keyDamp: int, keyFriction: int, keyFail: int, keyLock: int)`**

使用该类可创建连接器截面。<br/>
`name`为连接器截面名称，应传入字符串；<br/>
`iType`为连接器截面类型，应使用`enums`中定义的[`ConnSectType`](#connsecttype)类，如`ConnSectType.Translation`；<br/>
`keyStiff`为刚度模型本构类型，应使用`enums`中定义的[`ConnStiffType`](#connstifftype)类，如`ConnStiffType.Linear`；<br/>
`consElas`为常刚度；<br/>
`keyDamp`为阻尼模型类型，应使用`enums`中定义的[`ConnDampType`](#conndamptype)类，如`ConnDampType.Off`；<br/>
`keyFriction`为摩擦类型，应使用`enums`中定义的[`ConnFrictionType`](#connfrictiontype)类，如`ConnFrictionType.Off`；<br/>
`keyFail`为失效控制类型，应使用`enums`中定义的[`ConnFailType`](#connfailtype)类，如`ConnFailType.Off`；<br/>
`keyLock`为阻止控制类型，应使用`enums`中定义的[`ConnLockType`](#connlocktype)类，如`ConnLockType.Off`。<br/>
`ConnectorSection`类已预先定义了形参`iType = ConnSectType.Translation`，`keyStiff = ConnStiffType.Linear`，`consElas = 0`，`keyDamp = ConnDampType.Off`，`keyFriction = ConnFrictionType.Off`，`keyFail = ConnFailType.Off`与`keyLock = ConnLockType.Off`，故定义连接器截面时应至少传入形参`name`。<br/>

##### 2.7.6、连接器
> **`Connector(start: int, end: int, iDofs: list[int], iSects: list[int], iCoord: int, vy: list[float], vx: list[float])`**

使用该类可创建连接器。<br/>
`start`与`end`分别为开始节点号与结束节点号；<br/>
`iDofs`为自由度号；<br/>
`iSects`为各自由度对应的连接器截面号；<br/>
`iCoord`为坐标系类型，应使用`enums`中定义的[`ConnCoordType`](#conncoordtype)类，如`ConnCoordType.Auto`；<br/>
`iCoord = [[vy], [vx]]`为连接单元局部坐标系，1个表示局部`y`向，2个表示局部`x`和`y`向。<br/>
`Connector`类已预先定义了全部形参，即：`start = None`，`end = None`，`iDofs = None`，`iSects = None`，`iCoord = ConnCoordType.Auto`，`vy = None`与`vx = None`。<br/>

#### 2.8、荷载
> **`LoadCase(name: str)`**

使用该类可为模型创建荷载。<br/>
`name`为荷载名称，应传入字符串。<br/>
`LoadCase(name: str)`类可通过`add()`函数添加具体的[荷载](#loadtype)，如：<br/>

**`LoadCase("test").add(Cload(gnids: list[int], dof: list[int], value: list[float]))`**

##### 2.8.1、节点荷载
> **`Cload(gnids: list[int], dof: list[int], value: list[float])`**

使用该类可创建节点荷载。<br/>
`gnids`为作用位置节点号；<br/>
`dof`为自由度(荷载施加方向)，应使用`enums`中定义的[`FDof`](#fdof)类，如`FDof.Fy`；<br/>
`value`为与荷载施加方向相对应的节点荷载的值。<br/>
`Cload`类已预先定义了全部形参，即：`gnids = None`，`dof = None`与`value = None`。<br/>

##### 2.8.2、节点位移
> **`Cdisp(gnids: list[int], dof: list[int], value: list[float])`**

使用该类可创建节点位移。<br/>
`gnids`为作用位置节点号；<br/>
`dof`为节点位移自由度，应使用`enums`中定义的[`Dof`](#dof)类，如`Dof.Ux`，此处不适用于`Dof.All`和`Dof.Uxyz`；<br/>
`value`为与自由度相对应的节点位移的值。<br/>
`Cdisp`类已预先定义了全部形参，即：`gnids = None`，`dof = None`与`value = None`。<br/>

##### 2.8.3、线(单元/构件)荷载
> **`Elload(geids: list[int], type: int, subType: int, value: list[float], iCoord: int, coord: list[float], dir: list[int])`**

使用该类可创建线(单元/构件)荷载。<br/>
`geids`为作用位置(单元/构件)号；<br/>
`type`为荷载分布类型，应使用`enums`中定义的[`LoadDistributionType`](#loaddistributiontype)类，如`LoadDistributionType.Concentrated`；<br/>
`subType`为荷载作用类型，应使用`enums`中定义的[`LoadSubType`](#loadsubtype)类，如`LoadSubType.Force`；<br/>
`value`为线(单元/构件)荷载值；<br/>
`iCoord`为坐标系类型，若该值为`0`则表示总体坐标系，若该值为`1`则表示单元局部坐标系；<br/>
`coord`为荷载相对位置；<br/>
`dir`为荷载方向矢量。<br/>
`Elload`类已预先定义了全部形参，即：`geids = None`，`type = LoadDistributionType.Uniform`，`subType = LoadSubType.Force`，`value = None`，`iCoord = 0`，`coord = None`与`dir=None`。<br/>

##### 2.8.4、面(单元/构件)荷载
> **`Esload(geids: list[int], type: int, subType: int, value: list[float], iCoord: int, coord: list[float], dir: list[int])`**

使用该类可创建面(单元/构件)荷载。<br/>
`geids`为作用位置(单元/构件)号；<br/>
`type`为荷载分布类型，应使用`enums`中定义的[`LoadDistributionType`](#loaddistributiontype)类，如`LoadDistributionType.Concentrated`；<br/>
`subType`为荷载作用类型，应使用`enums`中定义的[`LoadSubType`](#loadsubtype)类，如`LoadSubType.Force`；<br/>
`value`为面(单元/构件)荷载值；<br/>
`iCoord`为坐标系类型，若该值为`0`则表示总体坐标系，若该值为`1`则表示单元局部坐标系；<br/>
`coord`为荷载相对位置；<br/>
`dir`为荷载方向矢量。<br/>
`Esload`类已预先定义了全部形参，即：`geids = None`，`type = LoadDistributionType.Uniform`，`subType = LoadSubType.Force`，`value = None`，`iCoord = 0`，`coord = None`与`dir = None`。<br/>

##### 2.8.5、面(单元/构件)边线荷载
> **`Eslload(esides: tumple, type: int, subType: int, value: list[float], iCoord: int, coord: list[float], dir: list[int])`**

使用该类可创建面(单元/构件)边线荷载。<br/>
`esides`为包含`geids: list[int]`(作用位置(单元/构件)号)与`sides: list[int]`(边号)的元组；<br/>
`type`为荷载分布类型，应使用`enums`中定义的[`LoadDistributionType`](#loaddistributiontype)类，如`LoadDistributionType.Concentrated`；<br/>
`subType`为荷载作用类型，应使用`enums`中定义的[`LoadSubType`](#loadsubtype)类，如`LoadSubType.Force`；<br/>
`value`为面(单元/构件)边线荷载值；<br/>
`iCoord`为坐标系类型，若该值为`0`则表示总体坐标系，若该值为`1`则表示单元局部坐标系；<br/>
`coord`为荷载相对位置；<br/>
`dir`为荷载方向矢量。<br/>
`Eslload`类已预先定义了全部形参，即：`esides = None`，`type = LoadDistributionType.Uniform`，`subType = LoadSubType.Force`，`value = None`，`iCoord = 0`，`coord = None`与`dir = None`。<br/>

##### 2.8.6、体荷载
> **`Ebload(geids: list[int], value: float, iCoord: int, dir: list[int])`**

使用该类可创建体荷载。<br/>
`geids`为作用位置单元号；<br/>
`value`为体荷载值；<br/>
`iCoord`为坐标系类型，若该值为`0`则表示总体坐标系，若该值为`1`则表示单元局部坐标系；<br/>
`dir`为荷载方向矢量。<br/>
`Ebload`类已预先定义了全部形参，即：`geids = None`，`value = 0`，`iCoord = 0`与`dir = None`。<br/>

##### 2.8.7、体(单元/构件)表面荷载
> **`Ebsload(esides: tumple, value: float, iCoord: int, dir: list[int])`**

使用该类可创建体(单元/构件)表面荷载。<br/>
`esides`为包含`geids: list[int]`(作用位置(单元/构件)号)与`sides: list[int]`(表面号)的元组；<br/>
`value`为体(单元/构件)表面荷载；<br/>
`iCoord`为坐标系类型，若该值为`0`则表示总体坐标系，若该值为`1`则表示单元局部坐标系；<br/>
`dir`为荷载方向矢量。<br/>
`Ebsload`类已预先定义了全部形参，即：`esides = None`，`value = 0`，`iCoord = 0`与`dir=None`。<br/>

##### 2.8.8、静水压力
> **`Wpload(esides: tumple, type: int, value: float, h0: float, h: float)`**

使用该类可创建静水压力。<br/>
`esides`为包含`geids: list[int]`(作用位置(单元/构件)号)与`sides: list[int]`(实体单元面号)的元组；<br/>
`type`为作用对象类型，应使用`enums`中定义的[`WaterPressureType`](#waterpressuretype)类，如`WaterPressureType.SolidSurface`；<br/>
`value`为参考点水压力；<br/>
`h0`为水平面坐标；<br/>
`h`为参考点坐标。<br/>
`Wpload`类已预先定义了全部形参，即：`esides = None`，`type = WaterPressureType.SolidSurface`，`value = 0`，`h0 = 0`与`h = 0`。<br/>

##### 2.8.9、动力波
> **`Wload(gnids: list[int], wType: int, value: float, timeHist:list[list[]], dir: list[int])`**

使用该类可创建动力波。<br/>
`gnids`为作用位置节点号；<br/>
`wType`为作用类型，应使用`enums`中定义的[`WaveType`](#wavetype)类，如`WaveType.Acceleration`；<br/>
`value`为荷载峰值；<br/>
`timeHist`为时程；<br/>
`dir`为荷载方向矢量。<br/>
`Wload`类已预先定义了全部形参，即：`gnids = None`，`wType = WaveType.Acceleration`，`value = 0`，`timeHist = None`与`dir = None`。<br/>

##### 2.8.10、节点温度
> **`Ctem(gnids: list[int], value: float)`**

使用该类可创建节点温度荷载。<br/>
`gnids`为作用位置节点号；<br/>
`value`为温度值。<br/>
`Ctem`类已预先定义了全部形参，即：`gnids = None`与`value = 0`。<br/>

#### 2.9、分析
##### 2.9.1、单元杀死激活
> **`Change(type=ChangeType.Add: int, geids = None)`**

使用该类可创建荷单元杀死激活。<br/>
`type`为单元生死类型，应使用`enums`中定义的[`ChangeType`](#changetype)类，如`ChangeType.Add`；<br/>
`geids`为作用单元。<br/>

##### 2.9.2、工况组合
> **`LoadCaseCombine(lid: int, coef = 1.0, PSDCurve = -1)`**

使用该类可创建工况组合。<br/>
`lid`为工况编号，为必填；<br/>
`coef`为组合系数，默认为1.0；<br/>
`PSDCurve`为功率谱密度曲线编号（仅用于随机振动分析中）。<br/>

##### 2.9.3、荷载步
> **`Step(name: str, changes=None: list[Change], loadCases=None: list[LoadCaseCombine])`**

使用该类可创建荷载步。<br/>
`name`为荷载步名称，应传入字符串；<br/>
`changes`为该荷载步的单元生死；<br/>
`loadCases`为该荷载步的组合工况<br/>
`Step`类已预先定义了形参`changes = None`与`loadCases = None`，故定义荷载步时应至少传入形参`name`。<br/>

##### 2.9.4、预应力/应变
> **`PreStress(geids: list[int], type: int, value: float)`**

使用该类可创建预应力/应变。<br/>
`geids`为预应力/应变作用位置单元号；<br/>
`type`为作用类型，应使用`enums`中定义的[`PreStressType`](#prestresstype)类，如`PreStressType.Stress`；<br/>
`value`为预应力/应变值。<br/>
`PreStress`类已预先定义了全部形参，即：`geids = None`，`type = PreStressType.Stress`与`value = 0`。<br/>

##### 2.9.5、初始速度
> **`InitialVelo(gnids: list[int], velo: list[float])`**

使用该类可创建初始速度。<br/>
`gnids`为作用位置节点号；<br/>
`velo`为速度矢量。<br/>
`InitialVelo`类已预先定义了全部形参，即：`gnids = None`与`velo = None`。<br/>

##### 2.9.6、随机振动分析相关
> **`SelfSpectrum(name: str, curves :list[list[float]], iType=0 :int, cType=0: int, iPropagation=0: int, speed=None: list[float], Rmax=0: float, Rmin=0: float)`**

使用该类可创建PSD自谱曲线。<br/>
`name`为曲线名；<br/>
`curves`为曲线[ [频率点], [频率点对应的值]]；<br/>
`iType`为PSD自谱曲线的类型（0,位移谱;1,速度谱;2,加速度谱;3,力谱;4,应力谱）；<br/>
`cType`为相关类型 (0: 完全不相关 1: 完全相关  3: 空间相关)；<br/>
`iPropagation`为是否考虑自谱曲线的行波效应(0表示不考虑, 1表示考虑)，某自谱曲线考虑行波效应则不能定义互谱曲线；<br/>
`speed`为传播速度传播速度[vx,vy,vz],仅在考虑行波效应时有效；<br/>
`Rmax`为最大部分相关范围，仅在空间相关（cType=3）时有效；<br/>
`Rmin`为最大完全相关范围，仅在空间相关（cType=3）时有效。<br/>

> **`CrossSpectrum(name: str, iPSD: int, iPSD2: int, curves :list[list[float]], iComplex=None: int)`**

使用该类可创建PSD互谱曲线。<br/>
`name`为曲线名；<br/>
`iPSD`为PSD曲线的编号；<br/>
`iPSD2`为PSD曲线2的编号；<br/>
`curves`为曲线[ [频率点], [频率点对应的实部值], [频率点对应的虚部值]]；<br/>
`iComplex`为该互谱曲线是否存在虚部值(0表示不存在, 1表示存在, 默认为0)；<br/>

> **`PSDCurve(selfSpectrum=None: list[SelfSpectrum], crossSpectrum=None: list[CrossSpectrum])`**

使用该类存放输入的PSD曲线。<br/>
`selfSpectrum`输入自谱曲线；<br/>
`crossSpectrum`输入互谱曲线。<br/>

##### 2.9.6、分析
> **`Analy(name: str, steps=None: list[Step], preStresses=None: list[PreStress], initialVelos=None: list[InitialVelo], psdCurve=None: list[PSDCurve])`**

使用该类可分析。<br/>
`name`为分析名称，应传入字符串；<br/>
`steps`为该分析的载荷步；<br/>
`preStresses`为该分析的预应力/应变；<br/>
`initialVelos`为该分析的初速度；<br/>
`psdCurve=None`为该分析所施加的功率谱密度曲线；<br/>
`Analy`类已预先定义了形参`steps = None`、`preStresses = None`、`initialVelos = None`与`psdCurve = None`，故定义分析时应至少传入形参`name`。<br/>

#### 2.10、模型修正
##### 2.10.1、节点铰接
> **`NodeJoint(gnids: list[int], type: int, geids: list[int])`**

使用该类可创建节点铰接。<br/>
`gnids`为作用位置节点号；<br/>
`type`为铰接类型，应使用`enums`中定义的[`JointType`](#jointtype)类，如`JointType.Sphere`；<br/>
`geids`为作用位置单元号。<br/>
`NodeJoint`类已预先定义了全部形参，即：`gnids = None`，`type = JointType.Sphere`与`geids = None`。<br/>

##### 2.10.2、节点附加质量
> **`NodeMass(gnids: list[int], mass: float)`**

使用该类可创建节点附加质量。<br/>
`gnids`为作用位置节点号；<br/>
`mass`为质量值。<br/>
`NodeMass`类已预先定义了全部形参，即：`gnids = None`与`mass = 0`。<br/>

##### 2.10.3、节点偏移
> **`NodeOffset(gnids: list[int], type: int, offset: list[float], sita: float, axisStart: list[float], axisEnd: list[float])`**

使用该类可创建节点偏移。<br/>
`gnids`为作用位置节点号；<br/>
`type`为偏移类型，应使用`enums`中定义的[`OffsetType`](#offsettype)类，如`OffsetType.Translation`；<br/>
`offset`为偏移量；<br/>
`sita`为旋转角；<br/>
`axisStart`为转轴起点；<br/>
`axisEnd`为转轴终点。<br/>
`NodeOffset`类已预先定义了全部形参，即：`gnids = None`，`type = OffsetType.Translation`，`offset = None`，`sita = 0`，`axisStart = None`与`axisEnd = None`。<br/>

##### 2.10.4、单元附加质量
> **`ElemMass(geids: list[int], mass: float)`**

使用该类可创建单元附加质量。<br/>
`geids`为作用位置单元号；<br/>
`mass`为质量值。<br/>
`ElemMass`类已预先定义了全部形参，即：`geids=None`与`mass = 0`。<br/>

##### 2.10.5、单元节点偏心
> **`ElemNodeOffcenter(geid: int, offCenter: list[list[float]])`**

使用该类可创建单元节点偏心。<br/>
`geid`为作用单元号；<br/>
`offCenter`为单元各节点x、y、z三个方向的偏心值。<br/>
`ElemNodeOffcenter`类已预先定义了形参`offCenter = None`，故定义单元节点偏心时应至少传入形参`geid`。<br/>

##### 2.10.6、单元截面偏心
> **`ElemSectOffcenter(geids: list[int], type: int, value: list[int])`**

使用该类可创建单元节点偏心。<br/>
`geids`为作用位置单元号；<br/>
`type`为偏心类型，应使用`enums`中定义的[`OffcenterType`](#offcentertype)类，如`OffcenterType.Beam`；<br/>
`value`为偏心值。<br/>
`ElemSectOffcenter`类已预先定义了全部形参，即：`geids = None`，`type = OffcenterType.Beam`与`value = None`。<br/>

##### 2.10.7、单元抑制
> **`ElemSuppress(geids: list[int])`**

使用该类可创建单元抑制。<br/>
`geids`为作用位置单元号。<br/>
`ElemSuppress`类未预先定义形参，故定义单元抑制时应至少传入形参`geids`。<br/>

##### 2.10.8、单元梁截面法向
> **`ElemNormal(normal: list[float], geids: list[int])`**

使用该类可创建单元梁截面法向。<br/>
`normal`为法向量；<br/>
`geids`为作用位置单元号。<br/>
`ElemNormal`类已预先定义了全部形参，即：`normal = None`与`geids = None`。<br/>

### 3、建立结构模型
结构模型的 `材料` 、 `截面` 、 `节点` 的建模方法与有限元相同 , 所不同之处是以 `构件` 取代了 `单元` 。
结构模型参数化建模支持两种模式, 即 `建筑结构模型` 和 `通用几何模型` 。

#### 3.1、建筑结构模型
##### 3.1.1、特殊边
> **`Edge(id=0, circleCenter=None: list[float], middles=None: list[int])`**

使用该类可创建 **特殊边** 作为建立结构构件的辅助数据结构, 所谓 **特殊边** 是指该边为圆弧或者有中间节点的情况<br/>
`id` 为该边在构件所有边中的编号, 从0开始;<br/>
`circleCenter` 为圆弧边的圆心, 当且仅当改边为圆弧时 ;<br/>
`middles` 为中间点的节点编号。<br/>

##### 3.1.2、梁柱撑构件
> **`BeamColumn(nids: list[int], iMark=ComponentType.BEAM, sid=-1,  normal=None: list[float], edge=None: Edge)`**

使用该类可创建 **梁柱撑等一维构件**<br/>
`nids` 为该构件所包含的节点编号;<br/>
`iMark` 为 **构件细分类型** , 应使用 `enums` 中定义的 [`ComponentType`](#componenttype) 类，如 `ComponentType.BEAM` ;<br/>
`sid` 为与构件相对应的截面的编号;<br/>
`normal` 为构件截面Y方向的方向向量;<br/>
`edge` 为特殊边属性, 当且仅当该一维构件为圆弧或者有中间节点时需要传入。<br/>
`BeamColumn` 类已预先定义了形参 `type = ComponentType.BEAM` , `sid = -1` 、 `normal = None` 与 `edge = None` , 故定义构件时应至少传入形参 `nids` 。<br/>

##### 3.1.3、墙构件
> **`Wall(nids: list[int], sid=-1, circleCenter=None: list[float], caveNids=None: list[int])`**

使用该类可创建 **墙构件**<br/>
`nids` 为该构件所包含的四个角点的节点编号, 需要符合左下角点、右下角点、右上角点、左上角点的顺序;<br/>
`sid` 为与构件相对应的截面的编号;<br/>
`circleCenter` 底边圆弧中心, 当且仅当为圆弧墙时需要传入;<br/>
`caveNids` 为墙洞的四个角点的节点编号, 需要符合左下角点、右下角点、右上角点、左上角点的顺序, 可与墙的节点重合, 当且仅当该构件开洞时需要传入。<br/>
`Wall` 类已预先定义了形参 `sid = -1` 、 `circleCenter = None` 与 `caveNids = None` , 故定义构件时应至少传入形参 `nids` 。<br/>

##### 3.1.4、楼板构件
> **`Plate(nids: list[int], sid=-1, edges=None: list[Edge])`**

使用该类可创建 **楼板构件**<br/>
`nids` 为该构件所包含的节点编号, 需要符合右手螺旋向上的顺序规则;<br/>
`sid` 为与构件相对应的截面的编号;<br/>
`edges` 为特殊边属性, 当且仅当有的板边为圆弧或有中间节点时需要传入;<br/>
`Plate` 类已预先定义了形参 `sid = -1` 与 `edges = None` , 故定义构件时应至少传入形参 `nids` 。<br/>

#### 3.2、通用几何模型
##### 3.2.1、几何线或线构件
> **`Line(start: int, end: int, center=None: int, kp=None: int, type=LineType.Straight, sid=-1, normal=None: list[float])`**

使用该类可创建 **几何线或线构件**<br/>
`start` 为该构件起点编号;<br/>
`end` 为该构件终点编号;<br/>
`center` 为该构件圆心点编号, `center` 与 `kp` 当且仅当几何线为圆弧线时需要传入;<br/>
`kp` 为该构件方向点编号, 若为-1则表示z向竖直向上, 若为-2则表示z向竖直向下;<br/>
`type` 为 **几何线类型** , 应使用 `enums` 中定义的 [`LineType`](#linetype) 类，如 `LineType.Straight` ;<br/>
`sid` 为与构件相对应的截面的编号;<br/>
`normal` 为构件截面Y方向的方向向量;<br/>
`Line` 类已预先定义了形参 `type = LineType.Straight` , `sid = -1` 与 `normal = None` , 故定义构件时应至少传入形参 `start` 、 `end` 。<br/>

##### 3.2.2、几何面或面构件
> **`Surf(outer: list[int], inners=None: list[list[int]], type=SurfType.Plane, bottom=-1, top=-1, sid=-1)`**

使用该类可创建 **几何面或面构件**<br/>
`outer` 为该构件外边界线的构件编号;<br/>
`inners` 为该构件内边界线(开洞)的构件编号;<br/>
`type` 为 **几何面类型** , 应使用 `enums` 中定义的 [`SurfType`](#surftype) 类，如 `SurfType.Plane` ;<br/>
`bottom` 当该构件为圆柱圆台或圆锥面时为底边线构件的编号;<br/>
`top` 当该构件为圆柱圆台面时为顶边线构件的编号, 当该构件为圆锥面时为顶点编号;<br/>
`sid` 为与构件相对应的截面的编号;<br/>
`Surf` 类已预先定义了形参 `type = SurfType.Plane` 与 `sid = -1` , 故定义构件时应至少传入形参 `outer` 。<br/>

##### 3.2.3、几何体或体构件
> **`Solid(outer: list[int], inners=None: list[list[int]], type=SolidType.General, sid=-1)`**

使用该类可创建 **几何体或体构件**<br/>
`outer` 为该构件外边界线的构件编号;<br/>
`inners` 为该构件内边界线(空腔)的构件编号;<br/>
`type` 为 **几何体类型** , 应使用 `enums` 中定义的 [`SolidType`](#solidtype) 类，如 `SolidType.General` ;<br/>
`sid` 为与构件相对应的截面的编号;<br/>
`Solid` 类已预先定义了形参 `type = SolidType.General` 与 `sid = -1` , 故定义构件时应至少传入形参 `outer` 。<br/>

### 4、条件查询(试验功能)
通过一定的查询条件(如属性编号、坐标范围、名称)进行节点、单元、材料、截面等元素信息的查询，并将查询结果聚合为一个临时集合，并支持将多种查询条件的结果进行并、交、差操作。<br/>
具体由查询实体(继承于`BaseQuery`类)和查询方法来组合实现。<br/>

#### 4.1、查询实体
##### 4.1.1、材料查询
> **`MaterialQuery(scope=None: set[Material]|list[Material]|list[int])`**

使用该类可进行 **材料** 的查询<br/>
`scope` 为本次查询所基于的元素范围或元素的id范围, 默认为所有元素。<br/>

##### 4.1.2、截面查询
> **`SectionQuery(scope=None: set[Section]|list[Section]|list[int])`**

使用该类可进行 **截面** 的查询<br/>
`scope` 为本次查询所基于的元素范围或元素的id范围, 默认为所有元素。<br/>

##### 4.1.3、节点查询
> **`NodeQuery(scope=None: set[Node]|list[Node]|list[int])`**

使用该类可进行 **节点** 的查询<br/>
`scope` 为本次查询所基于的元素范围或元素的id范围, 默认为所有元素。<br/>

##### 4.1.4、单元查询
> **`ElemQuery(scope=None: set[Element]|list[Element]|list[int])`**

使用该类可进行 **单元** 的查询<br/>
`scope` 为本次查询所基于的元素范围或元素的id范围, 默认为所有元素。<br/>

#### 4.2、查询方法
##### 4.2.1、查询结果
> **单个元素-`one`**
> **多个元素-`items`**
> **单个元素编号-`id`**
> **多个元素编号-`ids`**

##### 4.2.2、并集
> **`union(query: BaseQuery)`**

使用该方法可以将现有查询结果与query进行 **求并集** 操作<br/>
`query` 为另一个查询实体。<br/>

##### 4.2.3、交集
> **`intersection(query: BaseQuery)`**

使用该方法可以将现有查询结果与query进行 **求交集** 操作<br/>
`query` 为另一个查询实体。<br/>

##### 4.2.4、差集
> **`difference(query: BaseQuery)`**

使用该方法可以将现有查询结果与query进行 **求差集** 操作<br/>
`query` 为另一个查询实体。<br/>

##### 4.2.5、等于条件
> **`eq(k: str, v, tol=None)`**

使用该方法可以将现有查询结果基础上新增一个 **属性k等于v容差范围为tol** 的筛选条件<br/>
`k` 为属性名;<br/>
`v` 为属性值;<br/>
`tol` 为容差范围。<br/>

##### 4.2.6、大于条件
> **`gt(k: str, v, tol=None)`**

使用该方法可以将现有查询结果基础上新增一个 **属性k大于v(容差范围为tol)** 的筛选条件<br/>

##### 4.2.7、大于等于条件
> **`ge(k: str, v, tol=None)`**

使用该方法可以将现有查询结果基础上新增一个 **属性k大于等于v(容差范围为tol)** 的筛选条件<br/>

##### 4.2.8、小于条件
> **`lt(k: str, v, tol=None)`**

使用该方法可以将现有查询结果基础上新增一个 **属性k小于v(容差范围为tol)** 的筛选条件<br/>

##### 4.2.9、小于等于条件
> **`le(k: str, v, tol=None)`**

使用该方法可以将现有查询结果基础上新增一个 **属性k小于等于v(容差范围为tol)** 的筛选条件<br/>

##### 4.2.10、求最小
> **`min(k: str, tol=None)`**

使用该方法可以将现有查询结果基础上查询 **属性k最小值对应的元素(容差范围为tol)** 的筛选条件<br/>
`k` 为属性名;<br/>
`tol` 为容差范围, 即当属性k的最小值为vmin时，属性k值在[vmin-tol, vmin+tl]的范围都会被选中。<br/>

##### 4.2.11、求最大
> **`max(k: str, tol=None)`**

使用该方法可以将现有查询结果基础上查询 **属性k最大值对应的元素(容差范围为tol)** 的筛选条件<br/>

##### 4.2.12、单元对应的节点(仅NodeQuery支持)
> **`elems(elems： ElementQuery|list[Element]|list[int])`**

使用该方法可以查询 **elems所包括的所有单元的节点** <br/>
`elems` 可以为一个ElementQuery或单元元素数组或单元编号数组。<br/>

##### 4.2.13、节点对应的单元(仅ElementQuery支持)
> **`nodes(nodes： NodeQuery|list[Node]|list[int])`**

使用该方法可以查询 **nodes所包括的所有节点所从属的单元** <br/>
`nodes` 可以为一个NodeQuery或节点元素数组或节点编号数组。<br/>

## 三、附录
### 1、枚举值
#### MaterialType
<details>
<summary id="summary-2">MaterialType (材料类型) 枚举值</summary>

    - Custom         # 自定义
    - Concrete       # 混凝土
    - Steel          # 钢材
    - Rebar          # 钢筋

</details>

#### MaterialModel
<details>
<summary id="summary-2">MaterialModel (本构类型) 枚举值</summary>

    - Elastic                  # 通用-线弹性本构
    - MetalPlastic             # 金属-弹塑性本构
    - ConcretePlasticDamage    # 混凝土-塑性损伤本构
    - ConcreteDamage           # 混凝土-二维规范本构
    - ConcreteGuoZhang         # 混凝土-一维过张本构
    - ConcreteMander           # 混凝土-一维Mander本构
    - ConcreteCode             # 混凝土-一维规范本构
    - ConcreteHLH              # 混凝土-一维韩林海本构

</details>

#### SectionType
<details>
<summary id="summary-2">SectionType (截面类型) 枚举值</summary>

    - Line           # 线元截面
    - Surface        # 面元截面
    - Solid          # 实体截面

</details>

#### ShapeType
<details>
<summary id="summary-2">ShapeType (截面形状类型) 枚举值</summary>

    - SOLID          # 实体
    - RECTANGLE      # 矩形
    - CIRCLE         # 圆形
    - BOX            # 箱形
    - ISHAPE         # 工字形
    - CROSSING       # 十字形
    - TUBE           # 圆管形
    - LSHAPE         # L形
    - TSHAPED        # T形
    - TRAPEZOID      # 梯形
    - CROSSISHAPED   # 十字工字形
    - SINGLELAYER    # 壳

</details>

#### ComponentType
<details>
<summary id="summary-2">ComponentType (构件类型) 枚举值</summary>

    - BEAM                      # 梁
    - COLUMN                    # 柱
    - BRACE                     # 撑
    - WALL                      # 墙
    - PLATE                     # 楼板
    - SOLID                     # 体构件
    - LINE                      # 线构件
    - SURF                      # 面构件
    - RIGID                     # 刚臂
    - TRUSS                     # 桁架
    - SUPPORT                   # 减隔震构件
    - CABLE                     # 拉索
    - BEAM_REBAR                # 梁配筋
    - COLUMN_REBAR              # 柱配筋
    - WALLBC_REBAR              # 墙梁墙柱配筋
    - BEAM_STEEL                # 梁型钢
    - COLUMN_STEEL              # 柱型钢
    - BRACE_STEEL               # 撑型钢

</details>

#### LineType
<details>
<summary>LineType (几何线类型) 枚举值</summary>

    - Straight                  # 直线
    - Arc                       # 圆弧线

</details>

#### SurfType
<details>
<summary>SurfType (几何面类型) 枚举值</summary>

    - Plane                     # 平面
    - Cylinder                  # 圆柱圆台面
    - Cone                      # 圆锥面
    - TriPatch                  # 三角面片构成的离散面

</details>

#### SolidType
<details>
<summary>SolidType (几何体类型) 枚举值</summary>

    - General                   # 通用多面体

</details>

#### ElementType
<details>
<summary id="summary-2">ElementType (单元类型) 枚举值</summary>

    - BeamEuler                # 欧拉梁
    - BeamLink                 # 梁杆
    - Link                     # 二力杆
    - PlaneClassic             # 三维平面应力
    - PlateMitc                # mitc板
    - ShellAssembled           # 组合壳
    - ShellDegenerated         # 退化壳
    - Solid                    # 三维实体
    - Cable                    # 张拉索
    - Membrane                 # 膜
    - Penalty                  # 罚单元
    - SolidLaStrain            # 三维实体
    - ElasBeamEuler            # 弹性欧拉梁
    - RebarBeam                # 钢筋梁单元
    - RebarShell               # 钢筋层壳单元

</details>

#### LoadType
<details>
<summary id="summary-2">LoadType (荷载类型) 枚举值</summary>

    - Cload          # 节点荷载
    - Cdisp          # 节点位移
    - Elload         # 线(单元/构件)荷载
    - Esload         # 面(单元/构件)荷载
    - Eslload        # 面(单元/构件)边线荷载
    - Ebload         # 体荷载
    - Ebsload        # 体(单元/构件)表面荷载
    - Wpload         # 静水压力
    - Wload          # 动力波
    - Ctem           # 节点温度
    - Emload         # 惯性力

</details>

#### FDof
<details>
<summary id="summary-2">FDof (荷载施加方向) 枚举值</summary>

    - Fx
    - Fy
    - Fz
    - Mx
    - My
    - Mz

</details>

#### Dof
<details>
<summary id="summary-2">Dof (自由度) 枚举值</summary>

    - All
    - Uxyz
    - Ux
    - Uy
    - Uz
    - Phx
    - Phy
    - Phz

</details>

#### LoadDistributionType
<details>
<summary id="summary-2">LoadDistributionType (荷载分布类型) 枚举值</summary>

    - Concentrated   # 集中荷载
    - Uniform        # 均布荷载
    - Nonuniform     # 线性分布荷载
    - BodyForce      # 体力荷载

</details>

#### LoadSubType
<details>
<summary id="summary-2">LoadSubType (荷载作用类型) 枚举值</summary>

    - Force          # 力
    - Moment         # 弯矩

</details>

#### WaterPressureType
<details>
<summary id="summary-2">WaterPressureType (静水压力作用对象类型) 枚举值</summary>

    - SolidSurface   # 体表面 (体力)
    - ShellSurface   # 面单元 (均布)

</details>

#### WaveType
<details>
<summary id="summary-2">WaveType (动力波作用类型) 枚举值</summary>

    - Acceleration   # 加速度
    - Velocity       # 速度
    - Displacement   # 位移

</details>

#### InertiaType
<details>
<summary id="summary-2">InertiaType (惯性力作用类型) 枚举值</summary>

    - Translation    # 平动
    - Rotation       # 转动

</details>

#### BindingType
<details>
<summary id="summary-2">BindingType (绑定类型) 枚举值</summary>

    - SurfToSurf     # 面-面绑定
    - NodeToSurf     # 点-面绑定
    - NodeToNode     # 点-点绑定

</details>

#### DofMode
<details>
<summary id="summary-2">DofMode (自由度模式) 枚举值</summary>

    - Both           # 平动及转动自由度
    - Translation    # 仅平动自由度
    - Custom         # 自定义自由度(仅对耦合有效)

</details>

#### CouplingType
<details>
<summary id="summary-2">CouplingType (耦合类型) 枚举值</summary>

    - Rigid          # 运动耦合(刚性耦合)
    - Flexible       # 分布耦合(柔性耦合)

</details>

#### EmbededType
<details>
<summary id="summary-2">EmbededType (嵌入类型) 枚举值</summary>

    - NodeToElem     # 点体作用(节点嵌入单元)
    - NodeToNode     # 点点作用(节点-节点绑定)

</details>

#### ContactType
<details>
<summary id="summary-2">ContactType (接触类型) 枚举值</summary>

    - ElasToElas     # 弹性-弹性接触
    - RigidToElas    # 刚性-弹性接触

</details>

#### ContactMethod
<details>
<summary id="summary-2">ContactMethod (离散类型) 枚举值</summary>

    - NodeToSurf     # 点-面接触(用于破坏接触)
    - SurfToSurf     # 面-面接触(用于挤压接触)

</details>

#### ConnSectType
<details>
<summary id="summary-2">ConnSectType (连接器截面类型) 枚举值</summary>

    - Translation    # 用于平动
    - Rotation       # 用于转动

</details>

#### ConnStiffType
<details>
<summary id="summary-2">ConnStiffType (刚度模型本构类型) 枚举值</summary>

    - Linear         # 线弹性本构
    - Nonlinear      # 非线性弹性本构
    - MetalPlastic   # 金属弹塑性本构

</details>

#### ConnDampType
<details>
<summary id="summary-2">ConnDampType (阻尼模型类型) 枚举值</summary>

    - Off            # 无阻尼
    - Constant       # 常系数阻尼
    - Nonlinear      # 非线性阻尼

</details>

#### ConnFrictionType
<details>
<summary id="summary-2">ConnFrictionType (摩擦类型) 枚举值</summary>

    - Off            # 无摩擦
    - On             # 有摩擦

</details>

#### ConnFailType
<details>
<summary id="summary-2">ConnFailType (失效控制类型) 枚举值</summary>

    - Off            # 忽略失效
    - On             # 考虑失效

</details>

#### ConnLockType
<details>
<summary id="summary-2">ConnLockType (阻止控制类型) 枚举值</summary>

    - Off            # 忽略阻止
    - On             # 考虑阻止

</details>

#### ConnCoordType
<details>
<summary id="summary-2">ConnCoordType (坐标系类型) 枚举值</summary>

    - Auto           # 自动
    - Fixed          # 固定局部系
    - Follow         # 随动局部系

</details>

#### ChangeType
<details>
<summary id="summary-2">ChangeType (单元杀死激活类型) 枚举值</summary>

    - Remove         # 杀死
    - Add            # 激活

</details>

#### FixedType
<details>
<summary id="summary-2">FixedType (约束类型) 枚举值</summary>

    - Default        # 点约束
    - BaseLine       # 线约束

</details>

#### ElasSupportType
<details>
<summary id="summary-2">ElasSupportType (弹性支座类型) 枚举值</summary>

    - Soil           # 土弹簧(单向侧移)
    - Lateral        # 普通侧移弹簧
    - Rotational     # 普通转角弹簧

</details>

#### IsolationBearingType
<details>
<summary id="summary-2">IsolationBearingType (隔震支座类型) 枚举值</summary>

    - General        # 通用支座
    - GeneralRubber  # 普通叠层橡胶支座
    - PlumbumRubber  # 铅芯叠层橡胶支座
    - DampingRubber  # 高阻尼叠层橡胶支座
    - FrictionRubber # 摩擦摆橡胶支座
    - SlideRubber    # 弹性滑板橡胶支座

</details>

#### PreStressType
<details>
<summary id="summary-2">PreStressType (作用类型) 枚举值</summary>

    - Stress         # 预应力
    - Strain         # 预应变

</details>

#### JointType
<details>
<summary id="summary-2">JointType (铰接类型) 枚举值</summary>

    - Sphere         # 球铰
    - BeamEnd        # 杆端铰

</details>

#### OffsetType
<details>
<summary id="summary-2">OffsetType (偏移类型) 枚举值</summary>

    - Translation    # 坐标平移
    - Rotation       # 坐标绕轴旋转

</details>

#### OffcenterType
<details>
<summary id="summary-2">OffcenterType (偏心类型) 枚举值</summary>

    - Node           # 节点偏心
    - Beam           # 梁截面偏心
    - Shell          # 壳截面偏心

</details>




### 2、有限元模型
> #### 梁

?> &ensp;&ensp;Python代码

    from pypcae.enums import *
    from pypcae.comp import *
    from pypcae.fem import FemModel

    clc()
    mat = Material("test", E0=1, poisson=0, density=1)
    sec = Section("test", SectionType.Line, Arbitrary(mid=mat.id, area=1, Ix=1, Iy=1, Iz=1))
    nods = [Node(0, 0, 0), Node(0.5, 0, 0), Node(1, 0, 0)]
    e1 = Element(nids=[nods[0].id, nods[1].id], sid=sec.id, type=ElementType.BeamEuler)
    e2 = Element(nids=[nods[1].id, nods[2].id], sid=sec.id, type=ElementType.BeamEuler)
    Elset("test", [e1.id, e2.id])

    Fixed(nods[0].id, Dof.All)
    LoadCase("test").add(Cload(FDof.Fy, -1, nods[2].id))

    FemModel.toViewer()

?> &ensp;&ensp;效果

![logo](beam.png ":size=1000")

> #### 壳

?> &ensp;&ensp;代码

    from pypcae.enums import *
    from pypcae.comp import *
    from pypcae.fem import FemModel

    clc()
    mat = Material("test", E0=1, poisson=0, density=1)
    sec = Section("test", SectionType.Surface, SingleLayer(mid=mat.id, t=1.0))

    l = 1.0
    b = 1.0
    n = 20
    m = 20
    nods = []
    for i in range(n + 1):
        for j in range(m + 1):
            nods.append(Node(i * l / n, j * b / m, 0))
    eleset = []
    for i in range(n):
        for j in range(m):
            e = Element(nids=[nods[(m + 1) * i + j].id, nods[(m + 1) * (i + 1) + j].id, nods[(m + 1) * (i + 1) + j + 1].id,
                              nods[(m + 1) * i + j + 1].id], type=ElementType.ShellAssembled, sid=sec.id)
            eleset.append(e.id)
    Elset("test", eleset)
    for j in range(m + 1):
        Fixed( nods[j].id, Dof.All)
    loadCase = LoadCase("test")
    for j in range(m):
        loadCase.add(Cload(FDof.Fz, -1.0 / m / 2, nods[(m + 1) * n + j].id))
        loadCase.add(Cload(FDof.Fz, -1.0 / m / 2, nods[(m + 1) * n + j + 1].id))
    step = Step("test")
    step.add(LoadCaseCombine(loadCase.id, 1.0))
    analy = Analy("test")
    analy.add(step)

    FemModel.toViewer()

?> &ensp;&ensp;效果

![logo](shell.png ":size=1000")

> #### 实体

?> &ensp;&ensp;Python代码

    from pypcae.comp import *
    from pypcae.fem import FemModel

    clc()
    mat = Material("test-mat", E0=1, poisson=0, density=1)
    sec = Section("test-sect", SectionType.Solid, SolidSect(mat.id))

    l, b, h = 1.0, 1.0, 1.0
    n = 8
    N = n + 1
    NN = (n + 1) * (n + 1)

    nset = Nset("all")
    cload_nset = Nset("cload")
    for i in range(N):
        for j in range(N):
            for k in range(N):
                node = Node(i * l / n, j * b / n, k * h / n)
                if k == 0:
                    Fixed(node.id, Dof.Uxyz)
                nset.add(node.id)
                if j == 0:
                    cload_nset.add(node.id)

    elset = Elset("all")
    bsload_esides = []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                e = Element([nset.ids[i * NN + j * N + k], nset.ids[i * NN + (j + 1) * N + k],
                             nset.ids[i * NN + (j + 1) * N + k + 1], nset.ids[i * NN + j * N + k + 1],
                             nset.ids[(i + 1) * NN + j * N + k], nset.ids[(i + 1) * NN + (j + 1) * N + k],
                             nset.ids[(i + 1) * NN + (j + 1) * N + k + 1], nset.ids[(i + 1) * NN + j * N + k + 1]],
                            type=ElementType.Solid, sid=sec.id)
                elset.add(e.id)
                if k == n - 1:
                    bsload_esides.append((e.id, 5))

    loadCase = LoadCase("test-loadcase")
    loadCase.add(Cload(nset.id, dof=FDof.Fy, value=0.5)).add(Ebsload(bsload_esides, value=1, dir=[0, 0, -1]))
    Analy("test-analy").add(Step("test-step").add(LoadCaseCombine(loadCase.id, 1.0)))

    FemModel.toViewer()

?> &ensp;&ensp;效果

![logo](solid.png ":size=1000")

> #### 网壳

?> &ensp;&ensp;代码

    from pypcae.enums import *
    from pypcae.comp import *
    from pypcae.fem import FemModel
    import math

    clc()
    mat = Material("test")
    sec = Section("test", SectionType.Line, Circle(mat.id, 0.2))

    a, b, f = 30, 15, 7
    Kn, Kx, h0 = 10, 10, 50

    nodes = list()
    nodes.append([Node(0, 0, f + h0).id])
    for i in range(1, Kx + 1):
        t = 1 - i * (i + 1) / (Kx * (Kx + 1))
        z = f * t
        c = math.sqrt(1 - z * z / (f * f))
        thet = 0
        nodes.append([])
        while thet < 360:
            x = a * c * math.cos(thet * math.pi / 180)
            y = b * c * math.sin(thet * math.pi / 180)
            node = Node(x, y, z + h0)
            nodes[-1].append(node.id)
            thet += 360 / (Kn * i)
            if i == Kx:
                Fixed( node.id, Dof.All)

    links = list()
    for m in range(1, Kx + 1):
        for n in range(Kn * m):
            links.append(Element(nids=[nodes[m][n], nodes[m][(n + 1) % (Kn * m)]]))
    for m in range(Kn):
        links.append(Element(nids=[nodes[0][0], nodes[1][m]]))
    for rib in range(Kn):
        for m in range(1, Kx):
            links.append(Element(nids=[nodes[m][rib * m], nodes[m + 1][rib * (m + 1)]]))
            links.append(Element(nids=[nodes[m][rib * m], nodes[m + 1][rib * (m + 1) - 1]]))
            links.append(Element(nids=[nodes[m][rib * m], nodes[m + 1][rib * (m + 1) + 1]]))
    for m in range(2, Kx):
        for n in range(Kn * m):
            if n % m != 0:
                links.append(Element(nids=[nodes[m][n], nodes[m + 1][int(n + n / m)]]))
                links.append(Element(nids=[nodes[m][n], nodes[m + 1][int(n + n / m + 1)]]))

    for link in links:
        link.sid = sec.id
        link.dim = 1
        link.tid = ElementType.Link

    FemModel.toViewer()

?> &ensp;&ensp;效果

![logo](dome.png ":size=1000")

> #### 双曲抛物面

?> &ensp;&ensp;Python代码

    from pypcae.enums import *
    from pypcae.comp import *
    from pypcae.fem import FemModel
    import math

    clc()
    wx0, wx1, wy, wz0, wz1 = 52, 87, 52, 43, 73
    yn, zn = 36, 22
    center = [0, 0, 0]
    paraCache = {}
    tol = 1e-3


    def parabolaBottom(y):
        a = (wz1 - wz0) / (wy / 2) ** 2
        x, z = center[0], center[1] - a * y ** 2
        return [x, y, z]


    def parabolaTop(y):
        a = 0.5 * (wx1 - wx0) / (wy / 2) ** 2
        x, z = center[0] + wx0 / 2 + a * y ** 2, center[2] + wz0
        return [x, y, z]


    def parabola(y, z):
        if y not in paraCache:
            paraSolve(y)
        a, b = paraCache[y]["a"], paraCache[y]["b"]
        x = math.sqrt((z - b) / a)
        return [x, y, z]


    def paraSolve(y):
        top, bottom = parabolaTop(y), parabolaBottom(y)
        paraCache[y] = {"a": (top[2] - bottom[2]) / (top[0] ** 2), "b": bottom[2]}


    mat = Material("test", E0=1e6, poisson=0.2, density=1000)
    sec = Section("test", SectionType.Line, Circle(mat.id, 0.5))

    pts = []
    for i in range(yn + 1):
        y = center[1] - wy / 2 + i * wy / yn
        chain = []
        for j in range(zn + 1):
            h = wz0 - parabolaBottom(y)[2]
            z = parabolaBottom(y)[2] + j * h / zn
            chain.append(parabola(y, z))
        chain.reverse()
        for j in range(1, zn + 1):
            chain.append([-chain[zn - j][0], chain[zn - j][1], chain[zn - j][2]])
        for j in range(len(chain)):
            pts.append(Node(chain[j][0], chain[j][1], chain[j][2]))

    for i in range(yn + 1):
        for j in range(zn * 2):
            Element(sid=sec.id, type=ElementType.Link,
                    nids=[pts[i * (2 * zn + 1) + j].id, pts[i * (2 * zn + 1) + j + 1].id])
    for i in range(yn):
        for j in range(zn * 2 + 1):
            Element(sid=sec.id, type=ElementType.Link,
                    nids=[pts[i * (2 * zn + 1) + j].id, pts[(i + 1) * (2 * zn + 1) + j].id])

    FemModel.toViewer()

?> &ensp;&ensp;效果

![logo](hyperbolic.png ":size=1000")





### 3、结构模型
> #### 开洞立方体

?> &ensp;&ensp;Python代码

    from pypcae.enums import *
    from pypcae.comp import *
    from pypcae.stru import StruModel

    a, b = 1.0, 0.25

    nbox = [
        Node(0, 0, 0).id,
        Node(a, 0, 0).id,
        Node(a, a, 0).id,
        Node(0, a, 0).id,
        Node(0, 0, a).id,
        Node(a, 0, a).id,
        Node(a, a, a).id,
        Node(0, a, a).id,
    ]

    nhole = [
        Node(b, 0, b).id,
        Node(a - b, 0, b).id,
        Node(a - b, 0, a - b).id,
        Node(b, 0, a - b).id,
        Node(b, a, b).id,
        Node(a - b, a, b).id,
        Node(a - b, a, a - b).id,
        Node(b, a, a - b).id,
    ]

    wbox = [
        Line(nbox[0], nbox[1]).id,
        Line(nbox[1], nbox[2]).id,
        Line(nbox[2], nbox[3]).id,
        Line(nbox[3], nbox[0]).id,

        Line(nbox[4], nbox[5]).id,
        Line(nbox[5], nbox[6]).id,
        Line(nbox[6], nbox[7]).id,
        Line(nbox[7], nbox[4]).id,

        Line(nbox[1], nbox[5]).id,
        Line(nbox[2], nbox[6]).id,
        Line(nbox[3], nbox[7]).id,
        Line(nbox[0], nbox[4]).id
    ]

    whole = [
        Line(nhole[0], nhole[1]).id,
        Line(nhole[1], nhole[2]).id,
        Line(nhole[2], nhole[3]).id,
        Line(nhole[3], nhole[0]).id,

        Line(nhole[4], nhole[5]).id,
        Line(nhole[5], nhole[6]).id,
        Line(nhole[6], nhole[7]).id,
        Line(nhole[7], nhole[4]).id,

        Line(nhole[1], nhole[5]).id,
        Line(nhole[2], nhole[6]).id,
        Line(nhole[3], nhole[7]).id,
        Line(nhole[0], nhole[4]).id
    ]

    sbottom = Surf([wbox[0], wbox[1], wbox[2], wbox[3]]).id
    stop = Surf([wbox[4], wbox[5], wbox[6], wbox[7]]).id
    s1 = Surf([[wbox[0], wbox[8], wbox[4], wbox[11]], [whole[0], whole[1], whole[2], whole[3]]]).id
    s2 = Surf([wbox[1], wbox[9], wbox[5], wbox[8]]).id
    s3 = Surf([[wbox[2], wbox[10], wbox[6], wbox[9]], [whole[4], whole[5], whole[6], whole[7]]]).id
    s4 = Surf([wbox[3], wbox[11], wbox[7], wbox[10]]).id
    shole1 = Surf([whole[0], whole[8], whole[4], whole[11]]).id
    shole2 = Surf([whole[1], whole[9], whole[5], whole[8]]).id
    shole3 = Surf([[whole[2], whole[10], whole[6], whole[9]]]).id
    shole4 = Surf([whole[3], whole[11], whole[7], whole[10]]).id

    Solid([sbottom, stop, s1, s2, s3, s4, shole1, shole2, shole3, shole4])

    StruModel.toViewer()

?> &ensp;&ensp;效果

![logo](cube.png ":size=1000")

> #### 圆柱圆锥

?> &ensp;&ensp;Python代码

    from pypcae.enums import *
    from pypcae.comp import *
    from pypcae.stru import StruModel

    a, h1, h2 = 1.0, 1.0, 2.0

    n = [
        Node(0,  0,  0).id,
        Node(a,  0,  0).id,
        Node(-a, 0,  0).id,
        Node(0,  0, h1).id,
        Node(a,  0, h1).id,
        Node(-a, 0, h1).id,
        Node(0,  0, h2).id
    ]

    w = [
        Line(n[1], n[2], center=n[0], kp=n[6], type=LineType.Arc).id,
        Line(n[4], n[5], center=n[3], kp=n[6], type=LineType.Arc).id,
        Line(n[2], n[1]).id,
        Line(n[5], n[6]).id,
        Line(n[4], n[6]).id,
        Line(n[2], n[5]).id,
        Line(n[1], n[4]).id,
    ]

    s = [
        Surf(bottom=w[0], top=w[1], type=SurfType.Cylinder).id,
        Surf(bottom=w[1], top=n[6], type=SurfType.Cone).id,
        Surf([w[0], w[2]], type=SurfType.Plane).id,
        Surf([w[2], w[5], w[3], w[4], w[6]], type=SurfType.Plane).id,
    ]

    Solid([s[0], s[1], s[2], s[3]])

    StruModel.toViewer()

?> &ensp;&ensp;效果

![logo](arbitrary.png ":size=1000")

> #### 简单结构

?> &ensp;&ensp;Python代码

    from pypcae.enums import *
    from pypcae.comp import *
    from pypcae.stru import StruModel

    clc()
    mat = Material(name='测试材料')
    colSec = Section("col", SectionType.Line, Rectangle(mat.id, b=0.6, h=0.6))
    beamSec = Section("beam", SectionType.Line, Rectangle(mat.id, b=0.3, h=0.6))
    braceSec = Section("beam", SectionType.Line, Tube(mat.id, D=0.1, d=0.08))
    wallSec = Section("wall", SectionType.Surface, SingleLayer(mat.id, t=0.2))
    plateSec = Section("plate", SectionType.Surface, SingleLayer(mat.id, t=0.1))

    floorNum, a = 10,10

    nids = []
    for i in range(floorNum+1):
        z = i*3
        nids.extend([Node(0,0,z).id, Node(a,0,z).id, Node(2*a,0,z).id, Node(3*a,0,z).id,
        Node(0,a,z).id, Node(a,a,z).id, Node(2*a,a,z).id, Node(3*a,a,z).id])
        if i == 0:
            Fixed([nid for nid in nids], Dof.All)

    cols = []
    beams = []
    braces = []
    walls = []
    plates = []
    for i in range(floorNum):
        ibasePre = i*8
        ibase = (i+1)*8
        for j in range(8):
            e = BeamColumn([nids[ibasePre+j], nids[ibase+j]], ComponentType.COLUMN, sid=colSec.id, normal=[0, 1, 0])
            cols.append(e.id)
        for j in range(3):
            e1 = BeamColumn([nids[ibase+j], nids[ibase+(j+1)]], ComponentType.BEAM, sid=beamSec.id, normal=[0, 1, 0])
            e2 = BeamColumn([nids[ibase+4+j], nids[ibase+4+(j+1)]], ComponentType.BEAM, sid=beamSec.id, normal=[0, 1, 0])
            beams.extend([e1.id,e2.id])
        for j in range(4):
            e = BeamColumn([nids[ibase+j], nids[ibase+4+j]], ComponentType.BEAM, sid=beamSec.id, normal=[1, 0, 0])
            beams.append(e.id)

    for i in range(floorNum):
        ibasePre = i*8
        ibase = (i+1)*8
        e1 = BeamColumn([nids[ibasePre], nids[ibase+4]], ComponentType.BRACE, sid=braceSec.id, normal=[1, 0, 0])
        e2 = BeamColumn([nids[ibasePre+4], nids[ibase]], ComponentType.BRACE, sid=braceSec.id, normal=[1, 0, 0])
        braces.extend([e1.id,e2.id])
        e1 = BeamColumn([nids[ibasePre+3], nids[ibase+7]], ComponentType.BRACE, sid=braceSec.id, normal=[1, 0, 0])
        e2 = BeamColumn([nids[ibasePre+7], nids[ibase+3]], ComponentType.BRACE, sid=braceSec.id, normal=[1, 0, 0])
        braces.extend([e1.id,e2.id])

    for i in range(floorNum):
        ibasePre = i*8
        ibase = (i+1)*8
        e1 = Wall([nids[ibasePre+1], nids[ibasePre+5], nids[ibase+5], nids[ibase+1]], sid=wallSec.id)
        e2 = Wall([nids[ibasePre+2], nids[ibasePre+6], nids[ibase+6], nids[ibase+2]], sid=wallSec.id)
        walls.extend([e1.id,e2.id])

    for i in range(floorNum):
        ibase = (i+1)*8
        e1 = Plate([nids[ibase], nids[ibase+1], nids[ibase+5], nids[ibase+4]], sid=plateSec.id)
        e2 = Plate([nids[ibase+1], nids[ibase+2], nids[ibase+6], nids[ibase+5]], sid=plateSec.id)
        e3 = Plate([nids[ibase+2], nids[ibase+3], nids[ibase+7], nids[ibase+6]], sid=plateSec.id)
        plates.extend([e1.id,e2.id,e3.id])

    StruModel.toViewer()

?> &ensp;&ensp;效果

![logo](structure.png ":size=1000")



