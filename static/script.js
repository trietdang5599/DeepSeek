
let processedResults = []; // Lưu kết quả sau khi gọi API
let current_task = "";

//#region event handler
document.getElementById("message").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        document.querySelector("#input-container button").click();
    }
});

function handleKeyPress(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

function hideDownloadButton(){
    const downloadButton = document.getElementById("download-button");
    downloadButton.style.display = "none";
}

//#endregion

//#region processing file
function processFile(task) {
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
            processJSON(content, task);
        } else if (file.name.endsWith(".csv")) {
            processCSV(content, task);
        } else {
            alert("Only support for JSON or CSV file!");
        }
    };

    reader.readAsText(file);
}

function processCategoryFile() {
    const fileInput = document.getElementById("fileCategory");
    const file = fileInput.files[0];

    if (!file) {
        alert("Please choose a JSON file!");
        return;
    }

    const reader = new FileReader();

    reader.onload = function (event) {
        try {
            let content = event.target.result;
            if (!file.name.endsWith(".json")) {
                alert("Only JSON files are supported!");
                return;
            }
            content = fixJSON(content);
            let jsonData = JSON.parse(content);
            if (!Array.isArray(jsonData)) {
                alert("Invalid JSON format. It should be a list of objects.");
                return;
            }

            const categoryDict = {};
            jsonData.forEach(item => {
                if (item.category && item.relatedAspects) {
                    const aspects = item.relatedAspects.split(", ").map(a => a.trim());
                    categoryDict[item.category] = aspects;
                }
            });

            saveCategoryData(categoryDict);
            

        } catch (error) {
            console.error("Error parsing JSON:", error);
            alert("Invalid JSON file.");
        }
    };

    reader.readAsText(file);
}

function saveCategoryData(categoryDict) {
    console.log("Sending category data:", categoryDict);

    fetch("/api/save-categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(categoryDict)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("API Response:", data);
        alert("✅ Categories saved successfully!");
    })
    .catch(error => {
        console.error("Error sending data:", error);
        alert("❌ Failed to save categories. Please try again.");
    });
}


function fixJSON(content) {
    try {
        if (typeof content !== "string") {
            console.error("Input data is not in JSON format:", content);
            return null;
        }
        try {
            const parsed = JSON.parse(content);
            if (Array.isArray(parsed)) {
                return content;
            }
        } catch (err) {
        }
        
        const lines = content.trim().split("\n").map(line => line.trim()).filter(line => line);
        
        let records = [];
        lines.forEach(line => {
            try {
                const parsedLine = JSON.parse(line);
                if (Array.isArray(parsedLine)) {
                    records.push(...parsedLine);
                } else {
                    records.push(parsedLine);
                }
            } catch (e) {
                console.error("Error parsing line:", line, e);
            }
        });
        
        return JSON.stringify(records);
    } catch (error) {
        console.error("Error JSON:", error);
        return null;
    }
}

function processJSON(content, task) {
    try {
        content = fixJSON(content);
        const data = JSON.parse(content);

        if (!Array.isArray(data)) {
            alert("File JSON không hợp lệ. Cần danh sách các đối tượng.");
            return;
        }
        if(task == 'extractAspects'){
            sendRequests(data);
        }
        else{
            preprocessingData(data);
        }
    } catch (error) {
        console.error("Lỗi phân tích JSON:", error);
        alert("File JSON không hợp lệ.");
    }
}

function processCSV(content, task) {
    // Sử dụng PapaParse để phân tích nội dung CSV với header tự động
    const results = Papa.parse(content, {
        header: true,
        skipEmptyLines: true,
        trimHeaders: true,
        dynamicTyping: true
    });
    
    const data = results.data;
    const headers = results.meta.fields;
    
    // Kiểm tra sự tồn tại của các cột cần thiết
    const requiredColumns = ["asin", "user_id", "text"];
    const hasRequiredColumns = requiredColumns.every(col => headers.includes(col));
    
    if (!hasRequiredColumns) {
        alert("File CSV cần có các cột: asin, user_id, text");
        return;
    }
    
    // Gọi hàm xử lý tương ứng dựa vào task
    if (task === 'extractAspects') {
        sendRequests(data);
    } else {
        preprocessingData(data);
    }
}

function splitRecords(processedResults) {
    const newRecords = [];

    processedResults.forEach(record => {
        if (record.processedText && Array.isArray(record.processedText)) {
            record.processedText.forEach(sentence => {
                newRecords.push({
                    reviewId: record.reviewId,
                    asin: record.asin,
                    user_id: record.user_id,
                    text: sentence.trim() // Loại bỏ khoảng trắng thừa
                });
            });
        }
    });

    return newRecords;
}

// function processJSONForCategories() {
//     const fileCategory = document.getElementById("fileCategory");
//     const file = fileCategory.files[0];

//     if (!file) {
//         alert("Please choose a JSON file!");
//         return;
//     }

//     // Kiểm tra phần mở rộng file
//     if (!file.name.endsWith(".json")) {
//         alert("Please upload a valid JSON file.");
//         return;
//     }

//     const reader = new FileReader();

//     reader.onload = function (event) {
//         try {
//             // Đọc nội dung JSON
//             const content = event.target.result;
//             const jsonData = JSON.parse(content);

//             // Kiểm tra nếu dữ liệu là mảng danh sách các danh mục
//             if (!Array.isArray(jsonData)) {
//                 alert("Invalid JSON format. Expected an array of objects.");
//                 return;
//             }

//             // Kiểm tra định dạng của từng phần tử
//             const categoryDict = jsonData.reduce((acc, row) => {
//                 if (row.category && Array.isArray(row.relatedAspects)) {
//                     acc[row.category] = row.relatedAspects.map(item => item.trim());
//                 }
//                 return acc;
//             }, {});

//             if (Object.keys(categoryDict).length === 0) {
//                 alert("No valid data found in the JSON file!");
//                 return;
//             }

//             console.log("Processed Category Data:", categoryDict);
//             storeCategoriesToAPI(categoryDict);

//         } catch (error) {
//             alert("Error processing JSON file: " + error.message);
//         }
//     };

//     reader.readAsText(file);
// }

// // Hàm gửi dữ liệu danh mục lên API
// function storeCategoriesToAPI(categoryDict) {
//     Object.entries(categoryDict).forEach(([category, relatedAspects]) => {
//         fetch('/api/store', {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ category, relatedAspects })
//         })
//         .then(response => response.json())
//         .then(data => console.log("API Response:", data))
//         .catch(error => console.error("Error sending data to API:", error));
//     });
// }

//#endregion

//#region handle functions
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
        } else if (data.aspectTerms && data.aspectTerms.length > 0) {
            // Tạo danh sách aspects và sentiment
            let aspectList = "<ul>";
            aspectList += `<li style="width: 500px;overflow-wrap: break-word;">
                            <strong>Category:</strong> ${data.category} <br>
                        </li>`;
            data.aspectTerms.forEach(a => {
                let polarityColor = "gray"; // Mặc định màu trung tính
                if (a.polarity === "positive") polarityColor = "green";
                else if (a.polarity === "negative") polarityColor = "red";

                aspectList += `<li>
                                <strong>Term:</strong> ${a.term} <br>
                                <strong>Opinion:</strong> <em>${a.opinion}</em> <br>
                                <strong>Polarity:</strong> <span style="color:${a.polarity}">${a.polarity}</span>
                            </li>`;

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
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: item.text })
            });

            const result = await response.json();

            if (!result.error && result.aspectTerms && result.aspectTerms.length > 0) {
                // Lưu kết quả vào mảng
                processedResults.push({
                    reviewId: item.reviewId,
                    rating: item.rating,
                    asin: item.asin,
                    user_id: item.user_id,
                    text: item.text,
                    helpful_vote: item.helpful_vote,
                    verified_purchase: item.verified_purchase,
                    category: result.category,
                    aspectTerms: result.aspectTerms
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
    current_task = "extractAspects";
    progressText.innerText = "Extraction completed";
    downloadButton.style.display = "inline"; // Hiển thị nút tải kết quả
    
    setTimeout(() => {
        progressBar.style.display = "none";
    }, 2000);
}

//pre-processing data
async function preprocessingData(data) {
    processedResults = []; // Reset kết quả đã xử lý
    const totalRequests = data.length;
    let completedRequests = 0;

    // Lấy các thành phần giao diện để hiển thị tiến trình
    const progressBar = document.getElementById("progress-bar");
    const progressIndicator = document.getElementById("progress-indicator");
    const progressText = document.getElementById("progress-text");
    const downloadButton = document.getElementById("download-button");

    // Hiển thị thanh tiến trình và ẩn nút download ban đầu
    progressBar.style.display = "block";
    progressText.innerText = "Processing ... 0%";
    downloadButton.style.display = "none";

    // Duyệt qua từng phần tử của dữ liệu đầu vào
    for (let item of data) {
        if (!item.text) continue; // Bỏ qua nếu không có nội dung

        try {
            const response = await fetch("/run-preprocessing", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: item.text })
            });
            const result = await response.json();

            // Giả sử API trả về kết quả ở thuộc tính 'sentences'
            if (!result.error && result.sentences && result.sentences.length > 0) {
                processedResults.push({
                    reviewId: item.reviewId,
                    rating: item.rating,
                    asin: item.asin,
                    user_id: item.user_id,
                    text: item.text,
                    helpful_vote: item.helpful_vote,
                    verified_purchase: item.verified_purchase,
                    processedText: result.sentences  // Mảng các câu sau tiền xử lý
                });
            }
        } catch (error) {
            console.error("Error calling preprocessing API:", error);
        }

        // Cập nhật thanh tiến trình
        completedRequests++;
        const progressPercent = Math.round((completedRequests / totalRequests) * 100);
        progressIndicator.style.width = progressPercent + "%";
        progressText.innerText = `Processing ... ${progressPercent}%`;
    }

    current_task = "preProcessing";
    progressText.innerText = "Extraction completed";
    downloadButton.style.display = "inline"; // Hiển thị nút download

    setTimeout(() => {
        progressBar.style.display = "none";
    }, 2000);
}

function downloadResults() {
    if (processedResults.length === 0) {
        alert("There nothing to download");
        return;
    }
    if(current_task == "preProcessing"){
        processedResults = splitRecords(processedResults);
    }
    const jsonData = JSON.stringify(processedResults, null, 4);
    const blob = new Blob([jsonData], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "aspects_file.json";
    link.click();
}
//#endregion



