pixel-banana-suite/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── edit.py
│   │   │   │   ├── animate.py
│   │   │   │   └── agent_chat.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── comfy_client.py
│   │   │   │   ├── job_tracker.py
│   │   │   │   └── nano_banana.py
│   │   │   ├── workflows/
│   │   │   │   └── comfy/
│   │   │   │       ├── sprite_pose.json
│   │   │   │       └── upscale.json
│   │   │   └── prompts/
│   │   │       └── edit/
│   │   │           ├── system.md
│   │   │           └── instruction.md
│   │   ├── .env.example
│   │   └── requirements.txt
│   ├── web/
│   │   ├── src/
│   │   │   ├── lib/
│   │   │   │   └── api.ts
│   │   │   ├── components/
│   │   │   │   ├── BackendBanner.tsx
│   │   │   │   ├── StatusCard.tsx
│   │   │   │   ├── RecentJobs.tsx
│   │   │   │   ├── StatusDrawer.tsx
│   │   │   │   ├── ActionCards.tsx
│   │   │   │   ├── ChatDock.tsx
│   │   │   │   ├── layout/
│   │   │   │   │   └── Layout.tsx
│   │   │   │   └── ui/
│   │   │   │       ├── button.tsx
│   │   │   │       ├── input.tsx
│   │   │   │       ├── scroll-area.tsx
│   │   │   │       └── select.tsx
│   │   │   ├── App.tsx
│   │   │   ├── main.tsx
│   │   │   └── index.css
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── tsconfig.app.json
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   └── postcss.config.js
│   └── scripts/
│       ├── sprite_pose_cli.py
│       ├── nano_edit_cli.py
│       └── animate_cli.py
├── .gitignore
└── README.md