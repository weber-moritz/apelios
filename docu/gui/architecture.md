# Apelios GUI Architecture

## 1. Why Qt (PySide6)?

### Industry Standard
- Used in professional applications: Autodesk, VFX studios, aerospace, broadcasting
- 20+ years of maturity and stability
- Large community and extensive documentation

### Real-Time Video Streaming
- **Efficient frame rendering**: Qt's `QLabel` + `QPixmap` handles OpenCV frames smoothly
- **GPU acceleration available**: Can use `QOpenGLWidget` for heavy graphics
- **Non-blocking GUI**: Asyncio integration via `qasync` prevents freezing

### Overlay Graphics
- **QPainter API**: Draw directly on video frames with minimal latency
- **Hardware-accelerated**: Qt can use GPU for rendering
- **Flexible**: Draw shapes, text, detection boxes in real-time

### Cross-Platform
- Works on Linux, Windows, macOS
- Consistent look and feel across platforms

### Asyncio Integration
- `qasync` library seamlessly integrates asyncio with Qt event loop
- No threading complexity — single unified event loop
- Perfect for existing async codebase (`ArtNetController`, `VideoReceiver`)

### Alternatives Considered & Why They're Worse
| Framework | Pros | Cons | Verdict |
|-----------|------|------|---------|
| **Tkinter** | Built-in | Slow video rendering, limited styling, no GPU | ❌ Not suitable |
| **PyGTK** | Linux native | Not standard on other platforms | ❌ Limited |
| **PyOpenGL** | GPU acceleration | Too low-level, complex | ❌ Overkill |
| **Web (Electron/Flask)** | Modern | High latency, resource hungry | ❌ For streaming |
| **Qt (PySide6)** | ✅ All benefits | None significant | ✅ **Best choice** |

---

## 2. Application Architecture

### Overall Flow

```
┌─────────────────────────────────────────────────────────┐
│                      main_deck.py                       │
│                   (Application Entry Point)             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  QApplication (Qt)     │
            │  + QEventLoop (qasync) │
            └────────────┬───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌─────────┐   ┌──────────────┐  ┌──────────────┐
    │ GUI/    │   │ Background   │  │ SteamDeck    │
    │ View    │   │ Tasks        │  │ Thread       │
    │ (Qt)    │   │ (Asyncio)    │  │ (Independent)│
    │         │   │              │  │              │
    │ - Tabs  │   │ - ArtNet     │  │ - Reads IMU  │
    │ - Video │   │ - VideoRx    │  │ - Non-block  │
    │ - Buttons   │ - Callbacks  │  │              │
    └────┬────┘   └──────┬───────┘  └──────┬───────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
                          ▼
            ┌─────────────────────────┐
            │  Model (Business Logic) │
            │  - ArtNetController     │
            │  - VideoReceiver        │
            │  - SteamdeckInputs      │
            │  - Fixtures             │
            └─────────────────────────┘
```

### Process Flow (Startup)

```
1. main_deck.py runs
   ↓
2. Create QApplication & QEventLoop (qasync bridge)
   ↓
3. Create MainWindow (initializes GUI widgets)
   ↓
4. Create AppController (orchestrates logic)
   ↓
5. Call AppController.start()
   ├─ asyncio.ensure_future(artnet.start())      ← Async task
   ├─ asyncio.ensure_future(video_receiver())    ← Async task
   ├─ asyncio.ensure_future(steamdeck_loop())    ← Async task
   └─ deck.start()                               ← Starts SteamDeck's internal thread
   ↓
6. loop.run_forever()
   └─ Unified event loop runs everything:
      ├─ Processes Qt GUI events (clicks, redraws)
      ├─ Runs asyncio tasks (all coroutines)
      └─ Handles signals/slots between components
```

### Component Interaction

```
MainWindow (View)
    │
    ├─ Emits: settings_changed(dict)
    ├─ Receives: display_frame(cv2_frame)
    ├─ Receives: update_angles(pan, tilt)
    └─ Receives: update_status(message)
                 │
                 ▼ (connected to)
            AppController (Controller)
                 │
                 ├─ Controls: ArtNetController (Model)
                 ├─ Controls: VideoReceiver (Model)
                 ├─ Controls: SteamdeckInputs (Model)
                 │
                 └─ Listens to signals from MainWindow
                    └─ Updates Model based on UI changes
```

---

## 3. MVC Pattern Explained

### Model (Business Logic)

**What it is:** Pure application logic with no UI awareness.

**Components:**
```
src/apelios/
├── artnet/
│   └── ArtNetController  ← Sends DMX data to lighting console
├── video_receiver/
│   └── VideoReceiver     ← Receives WebRTC stream, detects people
├── steamdeck/
│   └── SteamdeckInputs   ← Reads gyro/button input
└── fixtures/
    └── Fixture loaders   ← Manages fixture definitions
```

**Key principle:** Model doesn't know the GUI exists.
```python
# Model example: ArtNetController
class ArtNetController:
    async def start(self):
        """Send Art-Net data. Doesn't care if there's a GUI."""
        while True:
            await self.send_dmx_data()
            await asyncio.sleep(0.01)
    
    def set_channel(self, channel, value):
        """Update a DMX channel. Pure logic, no UI code."""
        self.dmx_data[channel] = value
```

### View (User Interface)

**What it is:** Display data and accept user input. No business logic.

**Components:**
```
src/apelios/gui/
├── gui.py              ← MainWindow class
├── widgets/
│   ├── video_widget.py ← Video display + overlays
│   └── settings_widget.py ← IP config, sensitivity sliders
└── styles.qss          ← Styling (CSS for Qt)
```

**Key principle:** View only displays, doesn't decide.
```python
# View example: VideoTab
class VideoTab(QWidget):
    def display_frame(self, frame):
        """Just display the frame. Don't process it."""
        pixmap = cv2_to_qpixmap(frame)
        self.video_label.setPixmap(pixmap)
    
    def update_angles(self, pan, tilt):
        """Just update the label. Don't calculate anything."""
        self.angle_label.setText(f"Pan: {pan:.1f}° | Tilt: {tilt:.1f}°")
```

### Controller (Orchestration)

**What it is:** Glues Model and View together. Manages async tasks.

**Components:**
```
main_deck.py
└── AppController
    ├─ Coordinates all components
    ├─ Runs async tasks
    ├─ Connects GUI signals to model actions
    └─ Updates View from Model data
```

**Key principle:** Controller makes decisions based on Model and View.
```python
# Controller example: AppController
class AppController:
    def __init__(self, window: MainWindow):
        self.window = window      # View
        self.artnet = ArtNetController()  # Model
        self.deck = SteamdeckInputs(5.0)  # Model
        
        # Connect View signals to Controller
        self.window.settings_changed.connect(self.on_settings_changed)
    
    async def steamdeck_loop(self):
        """Read Model, update View. Pure orchestration."""
        angles = [0.0, 0.0]
        while True:
            delta = self.deck.getAngleAcceleration()  # Read Model
            angles[0] += delta[0]
            angles[1] += delta[1]
            
            # Update View
            self.window.update_angles(angles[0], angles[1])
            
            # Update Model
            self.artnet.set_channel(1, int(angles[0]))
            
            await asyncio.sleep(0.01)
    
    def on_settings_changed(self, settings):
        """Handle View signal, update Model."""
        self.artnet.target_ip = settings['target_ip']
        self.artnet.universe = settings['universe']
```

### Data Flow

```
User clicks button in View
    │
    ▼
View emits signal: button_pressed()
    │
    ▼
Controller receives signal: on_button_pressed()
    │
    ▼
Controller calls Model: model.do_something()
    │
    ▼
Model changes state: self.value = new_value
    │
    ▼
Controller reads Model: result = model.get_value()
    │
    ▼
Controller updates View: view.display(result)
    │
    ▼
View renders: GUI shows new data
```

### Why This Matters

| Benefit | Example |
|---------|---------|
| **Testability** | Test `ArtNetController` without Qt; test UI with mock Model |
| **Reusability** | Use Model in CLI app, web service, or new GUI |
| **Maintainability** | Fix UI bug without touching business logic, and vice versa |
| **Scalability** | Add new features to Model without touching View |
| **Professionalism** | Industry-standard pattern used everywhere |

---

## 4. Threading Model (qasync)

### Problem with Traditional Approaches

**Option 1: Two separate event loops (BAD)**
```python
asyncio.run(main())     # Blocks
app.exec()              # Never reached!
```

**Option 2: Two threads (Complex)**
```
Thread 1: Qt event loop
Thread 2: asyncio event loop
    └─ Must use Queue or locks for communication
    └─ Risk of deadlocks or race conditions
```

### Solution: Single Unified Event Loop (qasync)

**One event loop handles everything:**
```python
loop = QEventLoop(app)              # Qt-compatible asyncio loop
asyncio.set_event_loop(loop)

asyncio.ensure_future(artnet_task)  # Add async task
asyncio.ensure_future(video_task)   # Add async task

with loop:
    loop.run_forever()              # Single unified loop!
```

**What the loop manages:**
```
Single QEventLoop
├─ Qt GUI events (button clicks, redraws)
├─ Asyncio coroutines (all async/await code)
├─ Qt signals/slots (cross-component communication)
└─ SteamDeck thread communication (via Qt signals)
```

**Why this works:**
- No conflicts between event loops
- Seamless signal/slot integration
- Minimal overhead
- Existing async code works unchanged

---

## 5. File Structure

```
src/apelios/
├── main_deck.py                 ← Entry point + AppController
├── gui/
│   ├── __init__.py
│   ├── gui.py                   ← MainWindow + all tabs
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── video_widget.py      ← Video display + overlays
│   │   └── settings_widget.py   ← Configuration UI
│   └── styles.qss               ← Stylesheets (CSS for Qt)
├── artnet/
│   ├── __init__.py
│   └── controller.py            ← ArtNetController
├── video_receiver/
│   ├── __init__.py
│   └── receiver.py              ← VideoReceiver
├── steamdeck/
│   ├── __init__.py
│   └── controller.py            ← SteamdeckInputs
└── ...other modules...
```

---

## 6. Asyncio + Qt Execution Flow

```
1. main_deck.py: asyncio.run() replaced with loop.run_forever()
2. QEventLoop continuously asks:
   ├─ "Any Qt events?" (button clicks, window events)
   ├─ "Any asyncio tasks ready?" (coroutines yielding control)
   ├─ "Any signals/slots?" (cross-component communication)
   └─ Sleep microseconds if nothing to do
3. When Model data changes → emit signal → View updates
4. When User acts → emit signal → Controller → update Model
5. SteamDeck thread sends data → Qt signal → Controller → View
```

---

## 7. Summary

| Aspect | Implementation |
|--------|-----------------|
| **Framework** | PySide6 (Qt) with qasync |
| **Architecture** | MVC (Model-View-Controller) |
| **Threading** | Single qasync event loop (no thread conflicts) |
| **Async Tasks** | ArtNet, VideoReceiver, SteamDeck read loop |
| **Communication** | Qt signals/slots + asyncio |
| **Styling** | Qt stylesheets (.qss files) |
| **Entry Point** | main_deck.py (creates app + controller) |

This architecture is **professional**, **scalable**, and **maintainable**.
