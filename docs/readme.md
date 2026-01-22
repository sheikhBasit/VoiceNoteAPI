VoiceNote AI - Android Voice Note-Taking Reinvented

VoiceNote AI is a professional-grade, intelligent voice-taking and task-management application for Android. Unlike standard recorders, it uses high-performance AI models (Groq Whisper & Llama 3.1) to transform messy audio into structured insights, searchable summaries, and actionable tasks automatically synced to your system.
🚀 Key Features

    Intelligent Audio Pipeline: Utilizes Groq Whisper-large-v3-turbo for near-instant, high-fidelity transcription.

    AI Summary & Task Extraction: Automatically generates descriptive titles, 2-sentence summaries, and actionable tasks from your recordings.

    Floating Shortcut Hub: A persistent, draggable overlay that allows you to start recordings or access tasks from any app or even the lock screen.

    Actionable Tasks: Extracted tasks include automatic contact searching and direct integration with WhatsApp, Slack, and Google Meet.

    Advanced Security: Biometric authentication-ready and supports local encryption for sensitive notes.

    Deep System Integration: Automatically schedules reminders via WorkManager and extracts deadlines directly into your calendar.

    Failover Reliability: Built-in API key rotation and offline queuing ensure you never lose a thought due to rate limits or connectivity issues.

🛠️ Technical Stack

    Language: 100% Kotlin

    UI Framework: Jetpack Compose (Material 3)

    Architecture: MVVM with Clean Architecture principles

    Networking: Retrofit & OkHttp

    Local Storage: Room Database & DataStore

    AI Engine: Groq API (Whisper v3 & Llama 3.1)

    Background Processing: WorkManager (for reminders) & Foreground Services (for recording)

    DI Framework: Hilt/Dagger (Planned/Integrated)

📂 Project Structure
Plaintext

app/src/main/java/com/example/voicenote/
├── core/
│   ├── components/       # Reusable UI components
│   ├── security/         # Biometric and encryption logic
│   ├── service/          # Overlay & Voice recording services
│   └── utils/            # Action executors (WhatsApp, Slack, PDF)
├── data/
│   ├── model/            # Data classes (Note, Task, User)
│   ├── network/          # API interfaces (Groq, etc.)
│   └── repository/       # Data handling (Firestore, AI logic)
└── features/
    ├── home/             # Main dashboard UI & ViewModel
    ├── detail/           # Note view & AI interaction
    ├── tasks/            # Global task management
    └── settings/         # API & user profile settings

🚦 Getting Started
Prerequisites

    Android Studio Ladybug or newer

    JDK 17+

    Android SDK 24+ (Android 7.0)

    A Groq API Key (for transcription/summarization)

Installation

    Clone the repository:
    Bash

    git clone https://github.com/sheikhbasit/voicenote.git

    Open in Android Studio: Wait for Gradle sync to complete.

    Add API Keys: Navigate to ApiSettingsScreen within the app or configure your local.properties (if configured) with your Groq credentials.

    Run: Select your physical device or emulator and hit Run.

🛡️ Permissions

The app requires the following permissions for full functionality:

    RECORD_AUDIO: For capturing your notes.

    SYSTEM_ALERT_WINDOW: For the Floating Shortcut Hub.

    READ_CONTACTS: To assign tasks to specific people.

    POST_NOTIFICATIONS: For task reminders and recording status.

📝 License

This project is licensed under the MIT License - see the LICENSE file for details.