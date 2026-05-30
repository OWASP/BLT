# 🎙️ AI-Powered GitHub Sportscaster

A real-time, AI-powered leaderboard of GitHub repository activity with live play-by-play commentary! Watch as repositories compete for the top spots with an animated sportscaster announcing each event.

## 🎯 Features

### Live Activity Tracking
- **Real-Time Monitoring**: Monitors the latest GitHub public events globally
- **Configurable Scope**: Watch all of GitHub, specific organizations, repositories, or users
- **Event Filtering**: Filter by event types (Push, PR, Issues, Stars, Forks, Releases)

### Dynamic Leaderboard & Analytics
- **Activity Scoring**: Repositories ranked by weighted activity scores
- **Trending Indicators**: See which repos are climbing or falling in the rankings
- **Real-Time Stats**: Track total events, contributors, and activity scores
- **Animated Transitions**: Beautiful animations when repos change positions

### AI Commentary
- **Sports-Style Announcements**: AI-generated play-by-play commentary for each event
- **Configurable AI Backend**: Connect to OpenAI or any compatible API
- **Fallback Templates**: Built-in engaging commentary when AI is unavailable
- **Multiple Models**: Support for gpt-4o-mini, gpt-4o, o3-mini, and gpt-3.5-turbo

### Audio Features
- **Sound Effects**: Unique audio cues for each event type (Push, PR, Star, Fork, etc.)
- **Text-to-Speech**: Have the AI commentary read aloud by the browser
- **Mute Controls**: Toggle sound effects and TTS independently

### Channel System
- **All Activity**: See everything happening in real-time
- **🔥 Hot**: High-impact events (Pushes, PRs, Releases)
- **💻 Code**: Code-related activity (Pushes, PRs, Creates, Deletes)
- **👥 Social**: Community engagement (Stars, Forks, Issues, Comments)

### Visual Design
- **Animated Sportscaster**: SVG robot that "announces" each event
- **TV Screen Interface**: Retro-inspired broadcast display
- **Glassmorphic Cards**: Modern, beautiful UI components
- **Dark Theme**: Easy on the eyes for 24/7 streaming
- **Responsive Design**: Works on desktop, tablet, and mobile

### Configuration Options
- **Monitoring Scope**: Global, Organization, Repository, or User
- **Preset Channels**: Quick access to popular tech categories (Web, AI/ML, DevOps)
- **Refresh Speed**: Adjustable from 5-60 seconds
- **Auto-Protect**: Automatic rate limit throttling
- **Local Storage**: Settings persist across sessions

## 🚀 Live Demo

Visit the live page at: https://owasp-blt.github.io/Github_Sportscaster/

## 📖 How It Works

The page fetches data from the GitHub Events API and processes it in real-time:

1. **Event Collection**: Polls GitHub API for public events
2. **Smart Processing**: Filters duplicates, categorizes events
3. **Activity Scoring**: Weights events by type and recency
4. **Leaderboard Updates**: Ranks repositories by activity score
5. **AI Commentary**: Generates sports-style announcements
6. **Live Rendering**: Animates changes in real-time

### Event Weights
| Event Type | Weight |
|------------|--------|
| Release | 10 |
| Pull Request | 5 |
| Fork | 4 |
| Push | 3 |
| Issues | 2 |
| Create | 2 |
| Watch (Star) | 1 |
| Comments | 1 |

## 🛠️ Technical Details

### Architecture
- **Single Page App**: HTML + CSS + JavaScript
- **No Build Required**: Works directly from static hosting
- **Modular Design**: Separate classes for SoundEffects, TTS, AI Commentary, and Main Sportscaster

### Files
- `index.html` - Main UI structure and styling
- `sportscaster.js` - Core JavaScript functionality

### API Integration
- **GitHub Events API**: Real-time public events
- **Conditional Requests**: Uses ETags to minimize API calls
- **Rate Limit Protection**: Auto-throttling when limits are low
- **Demo Mode**: Fallback to simulated data if API is unavailable

### AI Integration
Configure your own AI API for commentary:
1. Click the ⚙️ Settings button
2. Enter your API URL (e.g., `https://api.openai.com/v1/chat/completions`)
3. Enter your API key
4. Select your preferred model
5. Enable AI Commentary with the 🤖 button

## 📝 Usage

### Basic Usage
Simply open the page and watch! The sportscaster will:
- Update every 10 seconds (configurable)
- Show new repositories as they appear
- Highlight repos with new activity
- Announce events with AI commentary (when enabled)

### Advanced Configuration

#### Monitor a Specific Organization
1. Open Settings (⚙️)
2. Set Scope to "Organization"
3. Enter org name (e.g., "facebook")
4. Click "Apply Configuration"

#### Monitor a Specific Repository
1. Open Settings (⚙️)
2. Set Scope to "Repository"
3. Enter repo (e.g., "facebook/react")
4. Click "Apply Configuration"

#### Enable AI Commentary
1. Open Settings (⚙️)
2. Enter your OpenAI API URL
3. Enter your API key
4. Select a model
5. Click "Apply Configuration"
6. Toggle the 🤖 button to enable

## 🔧 Development

To run locally:
```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/Github_Sportscaster.git
cd Github_Sportscaster

# Serve the files (any HTTP server works)
python3 -m http.server 8080

# Open http://localhost:8080 in your browser
```

## 🔒 Security Notes

- API keys are stored in browser localStorage
- No server-side processing of credentials
- All API calls made directly from browser
- Consider using environment-restricted API keys

## 📄 License

This project is open source and available under the MIT License.