# Apelios Diagrams - Official Style Guide

Quick reference for creating consistent, thesis-ready draw.io diagrams across all C4 levels.

## 1. Unified Color Palette

We use a soft, professional "Academic Blend" to ensure high contrast and print readability.

| Element | Fill | Stroke | Text | Usage |
| --- | --- | --- | --- | --- |
| **System / Components** | `#85bbf0` | `#0b4884` | `#000000` | Apelios core, Python App, internal layers |
| **Broker (NATS)** | `#D7BDE2` | `#884EA0` | `#000000` | The message bus component |
| **Data / JSON** | `#FAD7A1` | `#D68910` | `#000000` | Static configs, routing profiles |
| **External Hardware** | `#D3D8DF` | `#666666` | `#000000` | Steam Deck, Lighting Infrastructure |
| **Person** | `#6c8ebf` | `#405f87` | `#ffffff` | Lighting Operator |
| **L4 Interface Header** | `#e8f4f8` | `#0b4884` | `#000000` | Abstract Base Classes (`<<interface>>`) |
| **L4 Class Body** | `#ffffff` | *(matches hdr)* | `#000000` | Method/Attribute lists in UML diagrams |

---

## 2. Shapes & Formatting

### **C1 – C3 (Architectural Block Diagrams)**

* **Style:** Solid color fills.
* **Shapes:** Rounded Rectangles (`rounded=1`) for systems/containers. Ellipses for people. Cylinders for data.
* **Connectors:** Orthogonal lines (`edgeStyle=orthogonalEdgeStyle`), `1.5pt` thickness, dark gray (`#444444`). Use `<br>` in labels to stack text neatly.

### **C4 (UML Class Diagrams)**

* **Style:** Split-box "Swimlane" style.
* **Headers:** Use the component's color from the palette above (e.g., `#85bbf0` for standard classes, `#D7BDE2` for Broker classes).
* **Bodies:** Must remain pure white (`#ffffff`) so attribute/method lists are readable.
* **Borders:** `2pt` stroke matching the header's dark border color.
* **Font:** Monospace (Courier New/Consolas), size 11px for methods/attributes. `-` for private, `+` for public.

---

## 3. C4 UML Arrow Cheat Sheet

For Level 4 diagrams, strict UML notation is required to show exact code relationships:

| UML Arrow Type | Visual Style | Meaning in Code |
| --- | --- | --- |
| **Implements** | Dashed line ➔ Hollow Triangle | A concrete class signing the contract of an interface/ABC. |
| **Inherits** | Solid line ➔ Hollow Triangle | A child class extending a parent class to reuse its actual code. |
| **Aggregates (Has-A)** | Solid line ➔ Hollow Diamond | Dependency Injection. Class A holds Class B in a variable (`self._client`). |
| **Depends (Uses)** | Dashed line ➔ Open Arrow | Class A temporarily uses Class B, but doesn't store it permanently. |

---

## 4. General Layout Rules

* **Grid:** Always snap to a `10px` grid.
* **Sizing:** Standardize box sizes per diagram (e.g., `240x140` for C1-C3 blocks, minimum `220px` width for C4 classes to prevent text wrapping).
* **Hierarchy (C4):** Interfaces at the top, concrete managers in the middle, data models at the bottom.
* **Exporting:** Export as PNG/SVG with a **transparent background** and include a 10% border padding for clean thesis integration.