const table = document.getElementById('logTable');
let memoryStore = {};

async function fetchLogs() {
    try {
        const response = await fetch('http://localhost:8080/api/intakes');
        const logs = await response.json();

        table.innerHTML = '';

        if (logs.length === 0) {
            table.innerHTML = '<tr><td colspan="5">No patient records found in the intakes folder.</td></tr>';
            return;
        }

        logs.forEach(log => {
            const raw = log.raw_data;

            // Map directly to your actual JSON keys
            const patientName = raw.patient_name || "Unknown";
            const doctor = raw.selected_doctor || "Unassigned";
            const appt = raw.appointment_slot || "Pending";

            // Store for the lightbox
            memoryStore[log.id] = raw;

            const row = document.createElement('tr');
            row.innerHTML = `
            <td>${patientName}</td>
            <td>${log.callTime}</td>
            <td>${doctor}</td>
            <td>${appt}</td>
            <td><button class="view-btn" onclick="viewBrief('${log.id}')">View Brief</button></td>
            `;
            table.appendChild(row);
        });
    } catch (error) {
        console.error("Failed to fetch logs:", error);
        table.innerHTML = '<tr><td colspan="5">Error loading records. Is server.py running on port 8080?</td></tr>';
    }
}

window.viewBrief = function(fileId) {
    const data = memoryStore[fileId];

    if (!data) {
        document.getElementById('jsonContent').innerText = "Error: No data found.";
        document.getElementById('clinicianView').innerHTML = "<p>Error: No data found.</p>";
    } else {
        // 1. Populate the JSON Tab
        document.getElementById('jsonContent').innerText = JSON.stringify(data, null, 4);

        // 2. Parse Data for the Clinician Tab
        const ageGender = [data.patient_age, data.patient_gender].filter(Boolean).join(" / ");
        const ros = data.review_of_systems || {};
        const oldcarts = data.oldcarts_analysis || {};

        // Extract all positive symptoms from ROS categories
        let positiveRos = [];
        for (const [system, symptoms] of Object.entries(ros)) {
            if (system !== 'pertinent_negatives' && Array.isArray(symptoms)) {
                positiveRos = positiveRos.concat(symptoms);
            }
        }

        // 3. Build the Clinician HTML Template
        const clinicianHtml = `
        <div class="clinical-header">
        <h2>${data.patient_name || "Unknown Patient"} <span class="age-gender">(${ageGender})</span></h2>
        <p><strong>Chief Complaint:</strong> ${data.chief_complaint || "N/A"}</p>
        <p><strong>Appointed:</strong> ${data.selected_doctor || "Unassigned"} | ${data.appointment_slot || "Pending"}</p>
        </div>

        <div class="clinical-section">
        <h4>History of Present Illness (HPI)</h4>
        <div class="narrative-box">${data.transcript_summary || "No summary available."}</div>
        </div>

        <div class="clinical-grid">
        <div class="clinical-section">
        <h4>History of Present Illness (OLDCARTS)</h4>
        <ul class="oldcarts-list">
        <li><strong>Onset:</strong> ${oldcarts.onset || "N/A"}</li>
        <li><strong>Location:</strong> ${oldcarts.location || "N/A"}</li>
        <li><strong>Duration:</strong> ${oldcarts.duration || "N/A"}</li>
        <li><strong>Characteristics:</strong> ${oldcarts.characteristics || "N/A"}</li>
        <li><strong>Aggravating:</strong> ${oldcarts.aggravating_factors || "N/A"}</li>
        <li><strong>Alleviating:</strong> ${oldcarts.alleviating_factors || "N/A"}</li>
        <li><strong>Radiation:</strong> ${oldcarts.radiation || "N/A"}</li>
        <li><strong>Treatment Tried:</strong> ${oldcarts.treatment_tried || "N/A"}</li>
        <li><strong>Severity:</strong> ${oldcarts.severity || "N/A"}</li>
        </ul>
        </div>
        <div class="clinical-section">
        <h4>Review of Systems (ROS)</h4>
        <div class="tags-container">
        ${positiveRos.length > 0
            ? positiveRos.map(s => `<span class="tag tag-positive">${s}</span>`).join('')
            : "<span class='tag'>None reported</span>"}
            </div>
            <span class='tag'>None reported</span>
            <h4 class="mt-3">Pertinent Negatives</h4>
            <div class="tags-container">
            ${(ros.pertinent_negatives || []).map(s => `<span class="tag tag-negative">${s}</span>`).join('')}
            </div>
            </div>
            </div>
            `;
            document.getElementById('clinicianView').innerHTML = clinicianHtml;
    }

    // Force the modal to open on the Clinician tab by default
    document.querySelector('.tab-btn[onclick*="clinicianView"]').click();
    document.getElementById('briefModal').style.display = 'flex';
}

// Tab Switching Function
window.switchTab = function(event, tabId) {
    // Hide all tabs and remove active class from all buttons
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    // Show the targeted tab and highlight the clicked button
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');
}
fetchLogs();
