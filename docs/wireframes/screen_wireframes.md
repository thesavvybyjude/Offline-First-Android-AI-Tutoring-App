# Screen Wireframes - AI Tutor App

## 1. Login Screen

```
┌─────────────────────────────────────┐
│                                     │
│         AI Tutor                    │
│    Offline-First Learning           │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Student ID                 │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  School Code                │   │
│  └─────────────────────────────┘   │
│                                     │
│  ☑ Continue Offline               │
│                                     │
│  ┌─────────────────────────────┐   │
│  │        LOGIN                 │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Elements:**
- Title: "AI Tutor" with subtitle
- Input: Student ID (text field)
- Input: School Code (text field)
- Checkbox: "Continue Offline" (default checked)
- Button: LOGIN (blue background)

---

## 2. Dashboard Screen

```
┌─────────────────────────────────────┐
│ ← Dashboard                        │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────┐  ┌──────────┐        │
│  │ Streak   │  │ Due Today│        │
│  │ 7 days   │  │   12     │        │
│  └──────────┘  └──────────┘        │
│                                     │
│  ┌──────────┐  ┌──────────┐        │
│  │Retention │  │Mastered │        │
│  │  87%     │  │   48    │        │
│  └──────────┘  └──────────┘        │
│                                     │
│  ┌─────────────────────────────┐   │
│  │      START REVIEW           │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │       ASK TUTOR             │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │       SETTINGS             │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │       LOGOUT                │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Elements:**
- Header: Back button, "Dashboard" title
- Stats Grid (2x2):
  - Streak: "7 days"
  - Due Today: "12"
  - Retention: "87%"
  - Mastered: "48"
- Action Buttons:
  - START REVIEW (blue)
  - ASK TUTOR (purple)
  - SETTINGS (gray)
  - LOGOUT (red)

---

## 3. Tutor Chat Screen

```
┌─────────────────────────────────────┐
│ ← AI Tutor                          │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │ What is photosynthesis?    │   │ ← User
│  │ [blue bubble]              │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Photosynthesis is the      │   │
│  │ process by which plants    │   │
│  │ convert sunlight into      │   │
│  │ energy...                   │   │ ← AI
│  │ [gray bubble]              │   │
│  │                             │   │
│  │ 📄 Source: biology.txt     │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ How does it work?           │   │ ← User
│  │ [blue bubble]              │   │
│  └─────────────────────────────┘   │
│                                     │
│  [scrollable area]                 │
│                                     │
├─────────────────────────────────────┤
│ ┌─────────────────────────┐ ┌────┐ │
│ │ Ask a question...       │ │Send│ │
│ └─────────────────────────┘ └────┘ │
└─────────────────────────────────────┘
```

**Elements:**
- Header: Back button, "AI Tutor" title
- Chat Area (scrollable):
  - User messages: Blue bubbles, right-aligned
  - AI messages: Gray bubbles, left-aligned
  - Source chips: 📄 Source: filename below AI responses
- Input Area:
  - Text input: "Ask a question..."
  - Send button

---

## 4. Flashcard Review Screen

```
┌─────────────────────────────────────┐
│ ← Flashcard Review    1/20          │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  │                             │   │
│  │   What is photosynthesis?  │   │ ← Question
│  │                             │   │
│  │                             │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │      SHOW ANSWER            │   │
│  └─────────────────────────────┘   │
│                                     │
│  [Rating buttons hidden]            │
│                                     │
└─────────────────────────────────────┘
```

**After showing answer:**

```
┌─────────────────────────────────────┐
│ ← Flashcard Review    1/20          │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │   What is photosynthesis?  │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  │ The process by which plants │   │ ← Answer
│  │ convert sunlight into      │   │
│  │ energy...                   │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌──┬──┬──┬──┬──┐                │
│  │ 1│ 2│ 3│ 4│ 5│  ← Rating      │
│  └──┴──┴──┴──┴──┘                │
│                                     │
└─────────────────────────────────────┘
```

**Elements:**
- Header: Back button, "Flashcard Review", progress "1/20"
- Card Area:
  - Question (always visible)
  - Answer (hidden until "Show Answer" clicked)
  - Flip animation when revealing
- Action Buttons:
  - "SHOW ANSWER" (blue)
  - Rating buttons 1-5 (appear after answer shown)
    - 1: Complete failure
    - 2: Incorrect
    - 3: Hard
    - 4: Good
    - 5: Perfect

---

## 5. Settings Screen

```
┌─────────────────────────────────────┐
│ ← Settings                         │
├─────────────────────────────────────┤
│                                     │
│  Student Name                       │
│  ┌─────────────────────────────┐   │
│  │ John Doe                   │   │
│  └─────────────────────────────┘   │
│                                     │
│  Subject Focus                      │
│  ┌─────────────────────────────┐   │
│  │ English, Biology           │   │
│  └─────────────────────────────┘   │
│                                     │
│  Daily Review Limit                  │
│  ┌─────────────────────────────┐   │
│  │ ━━━●━━━━━━━━━━━━━━━━━━━ 20 │   │
│  └─────────────────────────────┘   │
│  20 cards/day                      │
│                                     │
│  Auto-Sync        ☑ ON             │
│                                     │
│  Storage Usage                      │
│  1.3 GB / 2.1 GB                   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │      CLEAR CACHE            │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │      SAVE SETTINGS          │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Elements:**
- Header: Back button, "Settings" title
- Student Name: Text input
- Subject Focus: Text input
- Daily Review Limit: Slider (5-50), value display
- Auto-Sync: Toggle switch
- Storage Usage: Display (e.g., "1.3 GB / 2.1 GB")
- Clear Cache: Button (orange)
- Save Settings: Button (blue)

---

## Design Specifications

### Colors
- **Primary Blue**: #3399CC (0.2, 0.6, 0.8)
- **Primary Purple**: #993399 (0.6, 0.2, 0.6)
- **Success Green**: #33CC66
- **Warning Orange**: #CC6633
- **Error Red**: #CC3333
- **Gray**: #808080
- **White**: #FFFFFF
- **Background**: #F5F5F5

### Typography
- **Title Font**: 32px, Bold
- **Header Font**: 24px, Bold
- **Body Font**: 16px, Regular
- **Small Font**: 14px, Regular
- **Input Font**: 16px, Regular

### Spacing
- **Padding**: 15px
- **Margin**: 10px
- **Button Height**: 50px
- **Card Height**: 200px

### Components
- **Buttons**: Rounded corners (8px), shadow
- **Cards**: White background, rounded corners (12px), shadow
- **Input Fields**: Border (1px #CCC), rounded corners (4px)
- **Chat Bubbles**: Rounded corners (16px), max width 80%
