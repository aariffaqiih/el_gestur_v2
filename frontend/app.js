const getBaseUrl = () => document.getElementById("api-url").value;

      const elConnStatus = document.getElementById("connection-status");
      const elEngineStatus = document.getElementById("status-engine");
      const elGesture = document.getElementById("val-gesture");
      const elLockedId = document.getElementById("val-locked-id");
      const elVoiceIcon = document.getElementById("voice-icon");
      const elVoiceBadge = document.getElementById("voice-status-badge");
      const elVoiceText = document.getElementById("voice-text");
      const elDocumentQuery = document.getElementById("document-query");
      const elDocumentMessage = document.getElementById("document-message");
      const elDocumentResults = document.getElementById("document-results");

      const videoStream = document.getElementById("video-stream");
      const videoPlaceholder = document.getElementById("video-placeholder");

      let recognition = null;
      let isBrowserVoiceRunning = false;
      let lastDocumentRevision = null;
      let voiceInputSource = "browser"; // "browser" or "backend"

      function setVoiceSource(source) {
        voiceInputSource = source;
        const btnBrowser = document.getElementById("btn-voice-browser");
        const btnBackend = document.getElementById("btn-voice-backend");
        const panelBackend = document.getElementById("backend-device-panel");
        const panelBrowser = document.getElementById("browser-info-panel");

        if (btnBrowser) btnBrowser.classList.remove("active");
        if (btnBackend) btnBackend.classList.remove("active");

        if (source === "browser") {
          if (btnBrowser) btnBrowser.classList.add("active");
          if (panelBackend) panelBackend.style.display = "none";
          if (panelBrowser) panelBrowser.style.display = "block";
        } else {
          if (btnBackend) btnBackend.classList.add("active");
          if (panelBackend) panelBackend.style.display = "block";
          if (panelBrowser) panelBrowser.style.display = "none";
          fetchVoiceDevices();
        }
      }

      async function fetchVoiceDevices() {
        try {
          const res = await fetch(`${getBaseUrl()}/voice_devices`);
          if (!res.ok) throw new Error("Gagal memuat perangkat audio backend");
          const data = await res.json();
          if (data.status === "success" && data.devices) {
            const selectEl = document.getElementById("backend-device-select");
            if (selectEl) {
              const currentVal = selectEl.value;
              selectEl.innerHTML = '<option value="default">Default System Mic (Backend)</option>';
              data.devices.forEach((device) => {
                const option = document.createElement("option");
                option.value = device.index;
                option.textContent = `[Idx ${device.index}] ${device.name}`;
                selectEl.appendChild(option);
              });
              // Restore selected value if still in options
              if (selectEl.querySelector(`option[value="${currentVal}"]`)) {
                selectEl.value = currentVal;
              }
            }
          }
        } catch (err) {
          console.error("Gagal mendapatkan daftar mikrofon backend:", err);
        }
      }

      async function onBackendDeviceChange(event) {
        const selectedValue = event.target.value;
        await apiCall("set_voice_device", "POST", { device_index: selectedValue });
      }

      let isVoiceMuted = false;

      function updateMuteButtonUI() {
        const btnMute = document.getElementById("btn-voice-mute");
        if (!btnMute) return;
        if (isVoiceMuted) {
          btnMute.className = "btn btn-success";
          btnMute.innerHTML = '<i class="fa-solid fa-microphone"></i> Aktifkan Suara';
        } else {
          btnMute.className = "btn btn-danger";
          btnMute.innerHTML = '<i class="fa-solid fa-microphone-slash"></i> Mute Suara';
        }
      }

      async function toggleVoiceMute() {
        const res = await apiCall("voice_toggle_mute", "POST");
        if (res && res.status === "success") {
          isVoiceMuted = res.is_muted;
          updateMuteButtonUI();
        }
      }

      async function toggleVoice(start) {
        if (start) {
          if (voiceInputSource === "browser") {
            await toggleBrowserVoice(true);
          } else {
            await toggleBackendVoice(true);
          }
        } else {
          // Stop both to ensure everything is off
          await toggleBrowserVoice(false);
          await toggleBackendVoice(false);
        }
      }

      async function toggleBackendVoice(start) {
        if (start) {
          await apiCall("voice_start", "POST");
        } else {
          await apiCall("voice_stop", "POST");
        }
      }

      async function toggleBrowserVoice(start) {
        const SpeechRecognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          console.warn(
            "Browser does not support Web Speech API. Falling back to backend VoiceTyper."
          );
          if (start) {
            await toggleBackendVoice(true);
          } else {
            await toggleBackendVoice(false);
          }
          return;
        }

        if (start) {
          if (isBrowserVoiceRunning) return;

          recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = "id-ID";

          recognition.onstart = () => {
            isBrowserVoiceRunning = true;
            elVoiceIcon.parentElement.classList.add("recording");
            elVoiceBadge.textContent = "LISTENING";
            elVoiceBadge.className = "status-badge badge-active";
            elVoiceText.textContent =
              "Mendengarkan langsung secara real-time...";
          };

          recognition.onresult = async (event) => {
            let finalTranscript = "";
            let interimTranscript = "";

            for (let i = 0; i < event.results.length; ++i) {
              const transcript = event.results[i][0].transcript;
              if (event.results[i].isFinal) {
                finalTranscript += transcript;
              } else {
                interimTranscript += transcript;
              }
            }

            elVoiceText.innerHTML = `
                        <span>${finalTranscript}</span>
                        <span style="color: var(--text-muted); font-style: italic;">${interimTranscript}</span>
                    `;

            for (let i = event.resultIndex; i < event.results.length; ++i) {
              if (event.results[i].isFinal) {
                const text = event.results[i][0].transcript.trim();
                if (text) {
                  console.log("Sending speech text to backend:", text);
                  await apiCall("type", "POST", { text });
                }
              }
            }
          };

          recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            if (event.error !== "no-speech") {
              elVoiceText.textContent = `Error: ${event.error}`;
              elVoiceText.style.color = "var(--danger)";
              stopBrowserVoice();
            }
          };

          recognition.onend = () => {
            if (isBrowserVoiceRunning && recognition) {
              try {
                recognition.start();
              } catch (e) {
                stopBrowserVoice();
              }
            }
          };

          recognition.start();
        } else {
          stopBrowserVoice();
        }
      }

      function stopBrowserVoice() {
        isBrowserVoiceRunning = false;
        if (recognition) {
          try {
            recognition.stop();
          } catch (e) {}
          recognition = null;
        }
        elVoiceIcon.parentElement.classList.remove("recording");
        elVoiceBadge.textContent = "IDLE";
        elVoiceBadge.className = "status-badge badge-inactive";
      }

      function updateVideoFeed() {
        videoStream.src = `${getBaseUrl()}/video_feed?t=${new Date().getTime()}`;
        videoStream.style.display = "block";
        videoPlaceholder.style.display = "none";
      }

      function handleImageError() {
        videoStream.style.display = "none";
        videoPlaceholder.style.display = "flex";
      }

      function formatFileSize(sizeInBytes) {
        if (!Number.isFinite(sizeInBytes) || sizeInBytes < 1024)
          return `${sizeInBytes || 0} B`;
        const units = ["KB", "MB", "GB"];
        let size = sizeInBytes / 1024;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
          size /= 1024;
          unitIndex += 1;
        }
        return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
      }

      function renderDocumentState(payload) {
        if (!payload) return;
        if (
          payload.revision !== undefined &&
          payload.revision === lastDocumentRevision
        )
          return;
        if (payload.revision !== undefined)
          lastDocumentRevision = payload.revision;

        elDocumentMessage.textContent =
          payload.message || "Status pencarian dokumen belum tersedia.";
        elDocumentMessage.classList.toggle("error", payload.status === "error");
        if (!Array.isArray(payload.results)) return;

        elDocumentResults.replaceChildren();
        if (payload.results.length === 0) {
          const emptyState = document.createElement("div");
          emptyState.className = "document-empty";
          emptyState.textContent =
            "Belum ada kandidat dokumen untuk ditampilkan.";
          elDocumentResults.appendChild(emptyState);
          return;
        }

        payload.results.forEach((documentResult, index) => {
          const resultCard = document.createElement("article");
          resultCard.className = "document-result";

          const resultIndex = document.createElement("div");
          resultIndex.className = "document-result-index";
          resultIndex.textContent = index + 1;

          const resultInfo = document.createElement("div");
          const resultName = document.createElement("div");
          resultName.className = "document-result-name";
          resultName.textContent = documentResult.name;

          const resultMeta = document.createElement("div");
          resultMeta.className = "document-result-meta";
          resultMeta.textContent = `${documentResult.extension.toUpperCase()} Â· ${formatFileSize(
            documentResult.size_bytes
          )} Â· ${new Date(documentResult.modified_at).toLocaleString(
            "id-ID"
          )}`;

          const resultPath = document.createElement("div");
          resultPath.className = "document-result-path";
          resultPath.textContent = documentResult.parent;

          const openButton = document.createElement("button");
          openButton.className = "btn btn-compact";
          openButton.type = "button";
          openButton.textContent = "Buka";
          openButton.setAttribute("aria-label", `Buka ${documentResult.name}`);
          openButton.addEventListener("click", () =>
            openDocument(documentResult.id)
          );

          resultInfo.append(resultName, resultMeta, resultPath);
          resultCard.append(resultIndex, resultInfo, openButton);
          elDocumentResults.appendChild(resultCard);
        });
      }

      async function searchDocuments(forceRefresh) {
        const query = elDocumentQuery.value.trim();
        if (!query) {
          renderDocumentState({
            status: "error",
            message: "Masukkan kata kunci dokumen yang ingin dicari.",
            revision: `local-${Date.now()}`,
          });
          return;
        }
        const payload = await apiCall("documents/search", "POST", {
          query,
          force_refresh: Boolean(forceRefresh),
        });
        renderDocumentState(payload);
      }

      async function openDocument(resultId) {
        const payload = await apiCall("documents/open", "POST", {
          result_id: resultId,
        });
        renderDocumentState(payload);
      }

      function handleDocumentCommandResponse(payload) {
        if (
          payload &&
          ["document_search", "document_open"].includes(payload.command)
        ) {
          renderDocumentState(payload);
        }
      }

      async function apiCall(endpoint, method = "POST", body = null) {
        try {
          const options = { method };
          if (body) {
            options.headers = { "Content-Type": "application/json" };
            options.body = JSON.stringify(body);
          }
          const res = await fetch(`${getBaseUrl()}/${endpoint}`, options);
          const data = await res.json();
          console.log(`[${endpoint}] Response:`, data);
          handleDocumentCommandResponse(data);
          if (endpoint === "start") updateVideoFeed();
          return data;
        } catch (err) {
          console.error(`[${endpoint}] Error:`, err);
        }
      }

      async function toggleLaser() {
        await apiCall("toggle_laser", "POST");
      }

      function setSoftware(software) {
        document
          .querySelectorAll(".software-btn")
          .forEach((btn) => btn.classList.remove("active"));
        document.getElementById(`btn-${software}`).classList.add("active");

        apiCall("set_software", "POST", { software });
      }

      async function openSoftwareApp(software) {
        await apiCall(`open_${software}`, "POST");
      }

      async function pollStatus() {
        try {
          const res = await fetch(`${getBaseUrl()}/status`);
          if (!res.ok) throw new Error("Network not ok");
          const data = await res.json();

          elConnStatus.textContent = "Connected";
          elConnStatus.className = "status-badge badge-active";

          if (data.is_active) {
            elEngineStatus.textContent = "ONLINE";
            elEngineStatus.className = "status-badge badge-active";
            if (
              videoStream.style.display === "none" &&
              !videoStream.src.includes("video_feed")
            ) {
              updateVideoFeed();
            }
          } else {
            elEngineStatus.textContent = "STANDBY";
            elEngineStatus.className = "status-badge badge-warning";
          }

          elLockedId.textContent = data.locked_id || "None";
          elGesture.textContent = data.gesture_status || "--";

          const btnLaser = document.getElementById("btn-toggle-laser");
          if (btnLaser) {
            if (data.gesture_status && data.gesture_status.includes("Laser")) {
              btnLaser.className = "btn btn-danger";
              btnLaser.innerHTML = '<i class="fa-solid fa-circle-dot"></i> Matikan Laser';
            } else {
              btnLaser.className = "btn";
              btnLaser.innerHTML = '<i class="fa-solid fa-circle-dot"></i> Aktifkan Laser Pointer';
            }
          }

          if (data.current_software) {
            document
              .querySelectorAll(".software-btn")
              .forEach((btn) => btn.classList.remove("active"));
            const btn = document.getElementById(`btn-${data.current_software}`);
            if (btn) btn.classList.add("active");
          }

          if (data.voice_typer) {
            const vt = data.voice_typer;
            isVoiceMuted = vt.is_muted || false;
            updateMuteButtonUI();

            if (isVoiceMuted) {
              elVoiceIcon.parentElement.classList.remove("recording");
              elVoiceIcon.className = "fa-solid fa-microphone-slash";
              elVoiceBadge.textContent = "MUTED";
              elVoiceBadge.className = "status-badge badge-warning";
            } else {
              elVoiceIcon.className = "fa-solid fa-microphone";
              if (isBrowserVoiceRunning) {
                elVoiceIcon.parentElement.classList.add("recording");
                elVoiceBadge.textContent = "LISTENING";
                elVoiceBadge.className = "status-badge badge-active";
              } else if (vt.is_running) {
                elVoiceIcon.parentElement.classList.add("recording");
                elVoiceBadge.textContent = vt.status.toUpperCase();
                elVoiceBadge.className = "status-badge badge-active";
              } else {
                elVoiceIcon.parentElement.classList.remove("recording");
                elVoiceBadge.textContent = "IDLE";
                elVoiceBadge.className = "status-badge badge-inactive";
              }
            }
            if (vt.last_text) {
              elVoiceText.textContent = vt.last_text;
            }
            if (vt.error && !isBrowserVoiceRunning) {
              elVoiceText.textContent = `Error: ${vt.error}`;
              elVoiceText.style.color = "var(--danger)";
            } else {
              elVoiceText.style.color = "var(--text-main)";
            }

            // Sync selected device in dropdown with backend
            const selectEl = document.getElementById("backend-device-select");
            if (selectEl && vt.device_index !== undefined) {
              const targetVal = vt.device_index === null ? "default" : vt.device_index.toString();
              if (selectEl.value !== targetVal && selectEl.querySelector(`option[value="${targetVal}"]`)) {
                selectEl.value = targetVal;
              }
            }
          }

          if (data.documents) {
            renderDocumentState(data.documents);
          }
        } catch (err) {
          elConnStatus.textContent = "Disconnected";
          elConnStatus.className = "status-badge badge-inactive";
        }
      }

      document
        .getElementById("api-url")
        .addEventListener("change", updateVideoFeed);
      videoStream.addEventListener("error", handleImageError);
      elDocumentQuery.addEventListener("keydown", (event) => {
        if (event.key === "Enter") searchDocuments(false);
      });

      // Initialize SpeechRecognition check and source mode
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        console.warn("Browser SpeechRecognition not supported, forcing Backend Server.");
        const btnBrowser = document.getElementById("btn-voice-browser");
        const btnBackend = document.getElementById("btn-voice-backend");
        if (btnBrowser) btnBrowser.style.display = "none";
        if (btnBackend) {
          btnBackend.style.gridColumn = "span 2";
          btnBackend.classList.add("active");
        }
        setVoiceSource("backend");
      } else {
        setVoiceSource("browser");
      }

      setInterval(pollStatus, 1000);
      pollStatus();