// AASHA Voice Recording & Speech-to-Text Studio
// Features: MediaRecorder (Audio capture & playback) + Web Speech API (Live Hindi/English STT) + AI Preview

let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;
let speechRecognizer = null;
let isRecording = false;
let recordingTimer = null;
let recordingSeconds = 0;

document.addEventListener('DOMContentLoaded', function () {
  const micBtn = document.getElementById('btnStartMic');
  const stopBtn = document.getElementById('btnStopMic');
  const recordAgainBtn = document.getElementById('btnRecordAgain');
  const audioPreviewContainer = document.getElementById('audioPlaybackContainer');
  const audioPlayer = document.getElementById('audioPlayer');
  const statusLabel = document.getElementById('recordingStatusLabel');
  const timerBadge = document.getElementById('recordingTimerBadge');
  const waveVisualizer = document.getElementById('recordingWave');
  const languageSelect = document.getElementById('voiceLanguage');
  const transcriptArea = document.getElementById('editedTranscript');
  const rawTranscriptInput = document.getElementById('rawTranscript');
  const previewBtn = document.getElementById('btnPreviewAI');
  const previewCard = document.getElementById('aiPreviewCard');
  const patientSelect = document.getElementById('patientSelect');

  // Check browser SpeechRecognition support
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const hasSpeechAPI = !!SpeechRecognition;

  if (!hasSpeechAPI) {
    const banner = document.getElementById('speechApiWarning');
    if (banner) banner.classList.remove('d-none');
  }

  // --- 1. Start Recording ---
  async function startRecording() {
    audioChunks = [];
    recordingSeconds = 0;
    transcriptArea.value = '';
    rawTranscriptInput.value = '';
    if (previewCard) previewCard.classList.add('d-none');
    if (audioPreviewContainer) audioPreviewContainer.classList.add('d-none');

    // Request Mic Audio Stream
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = function (e) {
        if (e.data && e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = function () {
        recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(recordedBlob);
        audioPlayer.src = audioUrl;
        audioPreviewContainer.classList.remove('d-none');

        // Create file object for form submission
        const audioFile = new File([recordedBlob], `recording_${Date.now()}.webm`, { type: 'audio/webm' });
        const container = new DataTransfer();
        container.items.add(audioFile);
        const fileInput = document.getElementById('audioFileInput');
        if (fileInput) fileInput.files = container.files;

        // Stop all audio tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
    } catch (err) {
      console.warn("Microphone access not available or blocked:", err);
      // Proceed with Speech API if permitted or manual fallback
    }

    // Initialize Web Speech API for live transcription
    if (hasSpeechAPI) {
      try {
        speechRecognizer = new SpeechRecognition();
        speechRecognizer.lang = languageSelect.value || 'hi-IN';
        speechRecognizer.continuous = true;
        speechRecognizer.interimResults = true;

        let accumulatedTranscript = '';

        speechRecognizer.onresult = function (event) {
          let interimTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const text = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              accumulatedTranscript += ' ' + text;
            } else {
              interimTranscript += text;
            }
          }
          const fullText = (accumulatedTranscript + ' ' + interimTranscript).trim();
          transcriptArea.value = fullText;
          rawTranscriptInput.value = fullText;
        };

        speechRecognizer.onerror = function (event) {
          console.warn("Speech recognition error:", event.error);
        };

        speechRecognizer.start();
      } catch (e) {
        console.warn("Could not start speech recognition:", e);
      }
    }

    // Update UI states
    isRecording = true;
    micBtn.classList.add('recording');
    micBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
    stopBtn.classList.remove('d-none');
    recordAgainBtn.classList.add('d-none');
    waveVisualizer.classList.remove('d-none');
    timerBadge.classList.remove('d-none');

    const langName = languageSelect.options[languageSelect.selectedIndex].text;
    statusLabel.innerHTML = `<span class="pulse-dot"></span> Listening in <strong>${langName}</strong>... Speak naturally now`;

    // Start timer
    recordingTimer = setInterval(() => {
      recordingSeconds++;
      const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
      const secs = String(recordingSeconds % 60).padStart(2, '0');
      timerBadge.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  // --- 2. Stop Recording ---
  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;

    // Stop timer
    if (recordingTimer) clearInterval(recordingTimer);

    // Stop MediaRecorder
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }

    // Stop Speech API
    if (speechRecognizer) {
      try {
        speechRecognizer.stop();
      } catch (e) {}
    }

    // Update UI states
    micBtn.classList.remove('recording');
    stopBtn.classList.add('d-none');
    recordAgainBtn.classList.remove('d-none');
    waveVisualizer.classList.add('d-none');
    statusLabel.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i> Recording finished. You can review, edit, or preview AI analysis below.';

    // Auto-trigger AI preview if text is present
    if (transcriptArea.value.trim().length > 5) {
      triggerAIPreview();
    }
  }

  // --- 3. Event Listeners ---
  if (micBtn) {
    micBtn.addEventListener('click', function () {
      if (!isRecording) {
        startRecording();
      } else {
        stopRecording();
      }
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', stopRecording);
  }

  if (recordAgainBtn) {
    recordAgainBtn.addEventListener('click', function () {
      startRecording();
    });
  }

  // Trigger preview button
  if (previewBtn) {
    previewBtn.addEventListener('click', function () {
      triggerAIPreview();
    });
  }

  // Preset Scenario Buttons
  const scenarioBtns = document.querySelectorAll('.btn-preset-scenario');
  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      const text = this.getAttribute('data-transcript');
      const lang = this.getAttribute('data-lang');
      if (text) {
        transcriptArea.value = text;
        rawTranscriptInput.value = text;
        if (lang && languageSelect) {
          languageSelect.value = lang;
        }
        statusLabel.innerHTML = `<i class="bi bi-lightning-charge-fill text-primary"></i> Preset scenario loaded: <em>"${escapeHtml(text.slice(0, 50))}..."</em>`;
        recordAgainBtn.classList.remove('d-none');
        triggerAIPreview();
      }
    });
  });

  // --- 4. Live AI Extraction & Triage Preview ---
  function triggerAIPreview() {
    const text = transcriptArea.value.trim();
    if (!text) {
      alert("Please record or enter a voice note first.");
      return;
    }

    const patientId = patientSelect ? patientSelect.value : null;
    const previewContainer = document.getElementById('aiPreviewCard');
    const loadingSpinner = document.getElementById('aiPreviewLoading');
    const resultContent = document.getElementById('aiPreviewResult');

    if (previewContainer) previewContainer.classList.remove('d-none');
    if (loadingSpinner) loadingSpinner.classList.remove('d-none');
    if (resultContent) resultContent.classList.add('d-none');

    fetch('/api/analyze-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transcript: text,
        patient_id: patientId
      })
    })
      .then(res => res.json())
      .then(data => {
        if (loadingSpinner) loadingSpinner.classList.add('d-none');
        if (resultContent) resultContent.classList.remove('d-none');

        const ext = data.extraction || {};
        const triage = data.triage || {};

        // 1. Triage Priority Badge
        const priorityBadge = document.getElementById('previewPriorityBadge');
        if (priorityBadge) {
          let badgeClass = 'badge-routine';
          let icon = '<i class="bi bi-shield-check"></i>';
          if (triage.priority === 'Urgent') {
            badgeClass = 'badge-urgent pulse-urgent';
            icon = '<i class="bi bi-exclamation-triangle-fill"></i>';
          } else if (triage.priority === 'Moderate') {
            badgeClass = 'badge-moderate';
            icon = '<i class="bi bi-clock-history"></i>';
          }
          priorityBadge.className = `badge-priority ${badgeClass}`;
          priorityBadge.innerHTML = `${icon} ${triage.priority_display || triage.priority}`;
        }

        // 2. Warning Flags
        const warningsList = document.getElementById('previewWarningsList');
        if (warningsList) {
          if (triage.warning_signs && triage.warning_signs.length > 0) {
            warningsList.innerHTML = triage.warning_signs.map(w => `
              <li class="text-danger fw-semibold small mb-1"><i class="bi bi-exclamation-circle-fill me-1"></i> ${escapeHtml(w)}</li>
            `).join('');
          } else {
            warningsList.innerHTML = '<li class="text-muted small"><i class="bi bi-info-circle me-1"></i> No critical red flags detected.</li>';
          }
        }

        // 3. Extracted Symptoms
        const symptomsContainer = document.getElementById('previewSymptomsList');
        if (symptomsContainer) {
          if (ext.symptoms && ext.symptoms.length > 0) {
            symptomsContainer.innerHTML = ext.symptoms.map(s => `
              <span class="badge bg-light text-dark border me-1 mb-1 p-2">${escapeHtml(s)}</span>
            `).join('');
          } else {
            symptomsContainer.innerHTML = '<span class="text-muted small">None specifically identified</span>';
          }
        }

        // 4. Duration, Observations, Medicines
        const durationEl = document.getElementById('previewDuration');
        if (durationEl) durationEl.textContent = ext.duration || 'Not specified';

        const obsEl = document.getElementById('previewObservations');
        if (obsEl) obsEl.textContent = ext.observations || 'None';

        const medEl = document.getElementById('previewMedicines');
        if (medEl) medEl.textContent = ext.medicines_mentioned || 'None mentioned';

        const pregEl = document.getElementById('previewPregnancy');
        if (pregEl) pregEl.textContent = ext.pregnancy_notes || 'Not applicable';

        // 5. Clinical Summary Text
        const summaryEl = document.getElementById('previewStructuredSummary');
        if (summaryEl) summaryEl.textContent = ext.structured_summary || '';

        // 6. Action Recommendation
        const actionEl = document.getElementById('previewAction');
        if (actionEl) actionEl.textContent = triage.recommended_action || 'Routine follow-up';
      })
      .catch(err => {
        console.error("Preview error:", err);
        if (loadingSpinner) loadingSpinner.classList.add('d-none');
      });
  }
});
