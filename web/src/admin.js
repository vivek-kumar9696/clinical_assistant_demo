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
    const fullJsonData = memoryStore[fileId];

    // Debug: Check if data exists in the console
    console.log("Viewing brief for:", fileId, fullJsonData);

    if (!fullJsonData) {
        document.getElementById('jsonContent').innerText = "Error: No data found for this record.";
    } else {
        document.getElementById('jsonContent').innerText = JSON.stringify(fullJsonData, null, 4);
    }

    document.getElementById('briefModal').style.display = 'flex';
}

fetchLogs();
