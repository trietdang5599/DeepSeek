document.getElementById("message").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        document.querySelector("#input-container button").click();
    }
});
function sendMessage() {
    const input = document.getElementById("message");
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    const chatLog = document.getElementById("chat-log");

    // Hiển thị tin nhắn người dùng
    const userMessage = document.createElement("div");
    userMessage.className = "message user";
    userMessage.innerHTML = `<strong>Bạn:</strong> ${message}`;
    chatLog.appendChild(userMessage);
    chatLog.scrollTop = chatLog.scrollHeight;

    // Gọi API Flask
    fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        const botMessage = document.createElement("div");
        botMessage.className = "message bot";

        if (data.error) {
            botMessage.innerHTML = `<strong>AI:</strong> <span class="error">${data.error}</span>`;
        } else if (data.aspects && data.aspects.length > 0) {
            // Tạo danh sách aspects và sentiment
            let aspectList = "<ul>";
            data.aspects.forEach(a => {
                let sentimentColor = "gray"; // Mặc định màu trung tính
                if (a.sentiment === "positive") sentimentColor = "green";
                else if (a.sentiment === "negative") sentimentColor = "red";

                aspectList += `<li><strong>${a.aspect}</strong>: <span style="color:${sentimentColor}">${a.sentiment}</span></li>`;
            });
            aspectList += "</ul>";

            botMessage.innerHTML = `<strong>AI:</strong> Aspects identified: <br>${aspectList}`;
        } else {
            botMessage.innerHTML = `<strong>AI:</strong> <span class="error">Không thể nhận diện các aspects.</span>`;
        }

        chatLog.appendChild(botMessage);
        chatLog.scrollTop = chatLog.scrollHeight;
    })
    .catch(error => {
        console.error("Lỗi:", error);
        const errorMessage = document.createElement("div");
        errorMessage.className = "message bot error";
        errorMessage.innerHTML = `<strong>AI:</strong> <span class="error">Lỗi kết nối API.</span>`;
        chatLog.appendChild(errorMessage);
    });
}

function resetChat() {
    fetch("/api/reset", { method: "POST" })
    .then(() => {
        document.getElementById("chat-log").innerHTML = "";
    })
    .catch(error => console.error("Lỗi:", error));
}

function handleKeyPress(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

let processedResults = []; // Lưu kết quả sau khi gọi API

function hideDownloadButton(){
    const downloadButton = document.getElementById("download-button");
    downloadButton.style.display = "none";
}

function processFile() {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];
    
    
    if (!file) {
        alert("Please choose JSON or CSV file!");
        return;
    }

    
    const reader = new FileReader();

    reader.onload = function (event) {
        const content = event.target.result;

        if (file.name.endsWith(".json")) {
            processJSON(content);
        } else if (file.name.endsWith(".csv")) {
            processCSV(content);
        } else {
            alert("Only support for JSON or CSV file!");
        }
    };

    reader.readAsText(file);
}

function fixJSON(content) {
    try {
        if (typeof content !== "string") {
            console.error("Input datas is not in JSON format:", content);
            return null;
        }

        const jsonObjects = content.trim().split("\n").map(line => line.trim()).filter(line => line);
        const fixedJson = "[" + jsonObjects.join(",") + "]";

        return fixedJson;
    } catch (error) {
        console.error("Error JSON:", error);
        return null;
    }
}

function processJSON(content) {
    try {
        content = fixJSON(content);
        const data = JSON.parse(content);

        if (!Array.isArray(data)) {
            alert("File JSON không hợp lệ. Cần danh sách các đối tượng.");
            return;
        }

        sendRequests(data);
    } catch (error) {
        console.error("Lỗi phân tích JSON:", error);
        alert("File JSON không hợp lệ.");
    }
}

function processCSV(content) {
    const lines = content.split("\n");
    const headers = lines[0].split(",");
    const data = [];

    if (!headers.includes("asin") || !headers.includes("user_id") || !headers.includes("text")) {
        alert("File CSV cần có các cột: asin, user_id, text");
        return;
    }

    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(",");
        if (values.length === headers.length) {
            let obj = {};
            headers.forEach((header, index) => {
                obj[header.trim()] = values[index].trim();
            });
            data.push(obj);
        }
    }

    sendRequests(data);
}

async function sendRequests(data) {
    processedResults = []; // Reset danh sách kết quả
    const totalRequests = data.length;
    let completedRequests = 0;

    // Lấy thanh tiến trình từ HTML
    const progressBar = document.getElementById("progress-bar");
    const progressIndicator = document.getElementById("progress-indicator");
    const progressText = document.getElementById("progress-text");
    const downloadButton = document.getElementById("download-button");
    
    progressBar.style.display = "block"; // Hiển thị thanh tiến trình
    progressText.innerText = "Processing ... 0%";
    downloadButton.style.display = "none"; // Ẩn nút tải kết quả

    for (let item of data) {
        if (!item.text) continue; // Bỏ qua dòng không có nội dung

        try {
            const response = await fetch("http://10.0.104.119:9099/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: item.text })
            });

            const result = await response.json();

            if (!result.error && result.aspects && result.aspects.length > 0) {
                // Lưu kết quả vào mảng
                processedResults.push({
                    asin: item.asin,
                    user_id: item.user_id,
                    text: item.text,
                    aspects: result.aspects
                });
            }
        } catch (error) {
            console.error("Error API:", error);
        }

        // Cập nhật tiến trình
        completedRequests++;
        const progressPercent = Math.round((completedRequests / totalRequests) * 100);
        progressIndicator.style.width = progressPercent + "%";
        progressText.innerText = `Processing ... ${progressPercent}%`;
    }

    progressText.innerText = "Extraction completed";
    downloadButton.style.display = "inline"; // Hiển thị nút tải kết quả
    
    setTimeout(() => {
        progressBar.style.display = "none";
    }, 2000);
}

function downloadResults() {
    if (processedResults.length === 0) {
        alert("There nothing to download");
        return;
    }

    const jsonData = JSON.stringify(processedResults, null, 4);
    const blob = new Blob([jsonData], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "aspects_file.json";
    link.click();
}
