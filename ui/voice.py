"""Speak a complaint instead of typing it. Uses the browser's speech recognition; no audio is stored or sent to the server."""
from collections.abc import Callable

import streamlit as st

from ui.icons import icon

_HTML = f"""\
<div class="cc-voice">
  <button id="mic" type="button" aria-pressed="false">{icon("mic", 16)}<span>Speak the complaint</span></button>
  <select id="lang" aria-label="Speech language">
    <option value="en-IN">English</option>
    <option value="hi-IN">हिन्दी</option>
  </select>
  <span id="status" aria-live="polite"></span>
</div>
"""

_CSS = """
.cc-voice { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; font: inherit; }
.cc-voice button, .cc-voice select {
  font: inherit; color: inherit; background: transparent; cursor: pointer;
  border: 1px solid rgba(128, 128, 128, 0.5); border-radius: 0.5rem; padding: 0.35rem 0.7rem;
  display: inline-flex; align-items: center; gap: 0.4rem;
}
.cc-voice button:disabled { opacity: 0.5; cursor: not-allowed; }
.cc-voice button[aria-pressed="true"] { border-color: #e5484d; color: #e5484d; }
.cc-voice #status { font-size: 0.85rem; opacity: 0.75; }
"""

_JS = """\
export default function (component) {
  const { parentElement, setTriggerValue } = component
  const mic = parentElement.querySelector("#mic")
  const lang = parentElement.querySelector("#lang")
  const status = parentElement.querySelector("#status")
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Recognition) {
    mic.disabled = true
    status.textContent = "Voice typing needs Chrome, Edge or Safari. Please type your complaint."
    return
  }
  let rec = null
  let finalText = ""
  mic.onclick = () => {
    if (rec) { rec.stop(); return }
    rec = new Recognition()
    rec.lang = lang.value
    rec.interimResults = true
    rec.continuous = false
    finalText = ""
    rec.onstart = () => {
      mic.setAttribute("aria-pressed", "true")
      status.textContent = "Listening... speak now"
    }
    rec.onresult = (e) => {
      let interim = ""
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i]
        if (r.isFinal) finalText += r[0].transcript
        else interim += r[0].transcript
      }
      status.textContent = (finalText + interim).trim() || "Listening... speak now"
    }
    rec.onerror = (e) => {
      const messages = {
        "not-allowed": "Microphone access is blocked. Allow it in your browser settings.",
        "no-speech": "No speech heard. Try again.",
      }
      status.textContent = messages[e.error] || "Voice input stopped. Try again."
    }
    rec.onend = () => {
      mic.setAttribute("aria-pressed", "false")
      const text = finalText.trim()
      rec = null
      if (text) {
        setTriggerValue("transcript", text)
        status.textContent = "Added to your complaint. Check it, then submit."
      }
    }
    rec.start()
  }
}
"""

_VOICE = st.components.v2.component("voice_complaint", html=_HTML, css=_CSS, js=_JS)


def voice_input(key: str, on_transcript: Callable[[], None]) -> None:
    """Mic button that calls on_transcript when a phrase is recognised. Read the text from st.session_state[key].transcript."""
    _VOICE(key=key, on_transcript_change=on_transcript)
