# GDSFactory Local Installation and Basic Usage Guide

Source page: <https://gdsfactory.github.io/gdsfactory/index.html>

## 1) Local Installation

```bash
pip install gdsfactory
```

Optional installer-based method (from the official docs):

```bash
pip install gdsfactory_install
gfi install
```

## 2) Installation Result in This Environment

- Python: `3.11.9`
- gdsfactory: `9.35.0` (successfully imported)

Use the command below to verify:

```bash
python -c "import gdsfactory as gf; print(gf.__version__)"
```

## 3) Quick Start (Official Example)

```python
import gdsfactory as gf

# Create a new component
c = gf.Component()

# Add a rectangle
r = gf.components.rectangle(size=(10, 10), layer=(1, 0))
rect = c.add_ref(r)

# Add text elements
t1 = gf.components.text("Hello", size=10, layer=(2, 0))
t2 = gf.components.text("world", size=10, layer=(2, 0))

text1 = c.add_ref(t1)
text2 = c.add_ref(t2)

# Position elements
text1.xmin = rect.xmax + 5
text2.xmin = text1.xmax + 2
text2.rotate(30)

# Show the result
c.show()
```

## 4) Basic Workflow (Summarized from Official Homepage)

1. **Design**  
   Define parametric cells (PCells) in Python to generate layouts and components.

2. **Verify**  
   Use DRC/DFM/LVS in the flow to ensure the layout matches design intent.

3. **Validate**  
   Connect layout, test protocols, and data analysis into a reusable validation loop.

## 5) Inputs and Outputs (Official Description)

- Input: Python / YAML
- Output: GDSII or OASIS (also supports STL and GERBER), plus associated settings and netlist data

## 6) References

- Official homepage: <https://gdsfactory.github.io/gdsfactory/index.html>
- Quick Start and docs navigation: <https://gdsfactory.github.io/gdsfactory/index.html#quick-start>

