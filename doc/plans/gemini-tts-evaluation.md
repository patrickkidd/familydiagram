# Plan: Gemini 3.1 Flash TTS for Personal App

## Context

macOS TTS quality in the Personal app is poor. Patrick wants to evaluate Gemini 3.1 Flash TTS as a replacement. Current TTS uses PyQt5's QTextToSpeech which delegates to NSSpeechSynthesizer on macOS — a deprecated API with limited voice quality.

## Findings

### Current State

- **Engine**: QTextToSpeech → NSSpeechSynthesizer (macOS), AVSpeechSynthesizer (iOS)
- **42 English voices available** on this Mac, but most are novelty (Boing, Bubbles, Zarvox, etc.)
- **Only 1 Premium voice installed**: "Zoe (Premium)"
- Default voice selection picks first female voice found → Karen (legacy Australian voice)
- Speech starts instantly (no network delay) via `personalappcontroller.py:sayAtIndex()`
- iOS uses AVSpeechSynthesizer which has access to better neural voices — this is primarily a macOS problem

### Gemini 3.1 Flash TTS

| Attribute | Value | Impact |
|-----------|-------|--------|
| Status | **Preview** (launched April 15, 2026) | API may change, rate limits unknown |
| Streaming | **Not supported** | Dealbreaker for UX — see below |
| Output | PCM 24kHz mono, base64 in JSON | 48KB/sec raw, ~3.8MB for 60sec response |
| Voices | 30 options (Kore, Puck, etc.) | Good variety |
| Cost | $20/1M output tokens (25 tok/sec) | ~$0.03/min of speech, ~$18/user/month at 20 exchanges/day |
| Quality | Elo 1211, top of Artificial Analysis leaderboard | Excellent |
| Features | Audio tags ([whispers], [excited]), scene direction | Nice for coaching context |

### The No-Streaming Problem

Current UX flow:
1. User waits 2-10s for AI text response from Claude/Gemini
2. Text appears → QTextToSpeech.say() starts within ~50ms
3. User hears speech almost immediately after seeing text

With Gemini TTS:
1. User waits 2-10s for AI text response
2. Text appears → fire TTS request → wait 3-10s more for full audio generation
3. **Total silence gap: 5-20 seconds** between sending a message and hearing any audio

For a therapy coaching app where conversational flow matters, this latency is unacceptable. Chunking (sentence-by-sentence) could reduce first-audio latency to ~1-2s but adds significant complexity (playback queue, gap handling, error recovery, 3-5x cost multiplier).

### HIPAA Blocker

Clinical discussion text would be sent to Google's Gemini API. Preview-status models are unlikely to be covered under Google Cloud's HIPAA BAA. This is a **hard blocker** for production use with real clinical data, regardless of technical feasibility.

### Cost Reality

At 20 exchanges/day with ~60s speech per response:
- Per user: ~$0.60/day = **~$18/month just for TTS**
- With sentence chunking (3-5 API calls per response): **~$54-90/month**
- Compare: local TTS = $0

## Recommendation

**Don't integrate Gemini 3.1 Flash TTS now.** Three blockers: no streaming (UX), preview status (stability), HIPAA (compliance). The quality is excellent but the delivery mechanism doesn't fit this use case.

### What to do instead

**Phase 1 — Improve local TTS (low effort, immediate):**

The real problem is that QTextToSpeech defaults to Karen (a legacy voice) and doesn't surface quality tiers. Only 1 Premium voice is installed on this Mac out of ~15+ available Premium voices for download.

Changes:
1. **`personalappcontroller.py`**: Change `_initTtsVoice()` to prefer Premium voices by checking for "(Premium)" in voice name. Change `_collectVoices()` to sort Premium voices first.
2. **`VoiceSettingsPage.qml`**: Add section headers (Premium / Standard / Novelty). Add a banner when no Premium voices are installed encouraging download.
3. No backend changes needed.

Ceiling: Premium voices through NSSpeechSynthesizer are decent but not neural-quality. This is a Qt 5.15 limitation — NSSpeechSynthesizer is deprecated and doesn't expose the latest Apple neural voices that AVSpeechSynthesizer does.

**Phase 2 — Cloud TTS via OpenAI (if Phase 1 insufficient):**

If local voice quality remains unacceptable, use OpenAI TTS instead of Gemini because:
- **Supports streaming** (critical for acceptable UX)
- **Production API** (not preview)
- **OpenAI HIPAA BAA** available for production tier
- **Lower cost**: tts-1 at $15/1M chars ≈ $0.50/day vs $0.60/day
- Anthropic SDK already in use on the backend

Architecture:
- New endpoint `POST /personal/tts` in btcopilot (backend proxy, keeps API key server-side)
- Returns binary `audio/mpeg` stream (not base64-in-JSON)
- Client receives audio stream via QNetworkReply, plays via QMediaPlayer/QAudioOutput
- Falls back to local QTextToSpeech when offline
- Provider-agnostic interface so Gemini TTS can swap in later when it supports streaming + exits preview

**Phase 3 — Revisit Gemini TTS (when ready):**

Swap Gemini TTS into the Phase 2 backend proxy when:
- Exits preview status
- Supports streaming
- Confirmed under Google Cloud HIPAA BAA

## Decision Needed

Phase 1 is low-risk and worth doing regardless. The question is whether Patrick wants to pursue Phase 2 (cloud TTS) given the cost and complexity, or whether improved local voices are sufficient.

## Files

| File | Role |
|------|------|
| `familydiagram/pkdiagram/personal/personalappcontroller.py:122-450` | TTS engine, voice selection, playback |
| `familydiagram/pkdiagram/resources/qml/Personal/VoiceSettingsPage.qml` | Voice settings UI |
| `familydiagram/pkdiagram/resources/qml/Personal/DiscussView.qml:99-107` | Auto-read trigger on AI response |
| `btcopilot/btcopilot/llmutil.py` | Gemini client factory (Phase 2+) |
| `btcopilot/btcopilot/personal/routes/` | Where TTS endpoint would go (Phase 2) |
