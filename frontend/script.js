
const API_BASE = "http://127.0.0.1:8000";

let token = localStorage.getItem("smart_mess_token");
let currentUser = null;
let currentStudents = [];
let currentMenu = null;


/* =========================================================
   BASIC HELPERS
========================================================= */

function escapeHtml(value){
    if(value === null || value === undefined){
        return "";
    }

    return String(value)
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");
}


function todayString(){
    const now = new Date();

    const year = now.getFullYear();
    const month = String(now.getMonth()+1).padStart(2,"0");
    const day = String(now.getDate()).padStart(2,"0");

    return `${year}-${month}-${day}`;
}


function formatDate(value){

    if(!value){
        return "—";
    }

    const parts = String(value).split("-");

    if(parts.length === 3){
        return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }

    return value;
}


function formatNumber(value){

    const n = Number(value || 0);

    return n.toFixed(2);
}


function capitalize(value){

    if(!value){
        return "";
    }

    return String(value).charAt(0).toUpperCase() +
        String(value).slice(1);
}


function showToast(message,error=false){

    const toast = document.getElementById("toast");

    toast.textContent = message;
    toast.classList.toggle("error",error);
    toast.classList.add("show");

    setTimeout(()=>{
        toast.classList.remove("show");
    },3000);
}


/* =========================================================
   API
========================================================= */

async function api(path,options={}){

    const headers = options.headers || {};

    if(token){
        headers["Authorization"] = `Bearer ${token}`;
    }

    if(options.body && !(options.body instanceof FormData)){
        headers["Content-Type"] = "application/json";
    }

    options.headers = headers;

    const response = await fetch(API_BASE + path,options);

    if(response.status === 401){

        localStorage.removeItem("smart_mess_token");
        token = null;

        showLogin();

        throw new Error("Session expired. Please login again.");
    }

    let data = null;

    const contentType = response.headers.get("content-type") || "";

    if(contentType.includes("application/json")){
        data = await response.json();
    }else{
        data = await response.text();
    }

    if(!response.ok){

        let message = "Request failed";

        if(data && data.detail){
            message = Array.isArray(data.detail)
                ? data.detail.map(x=>x.msg).join(", ")
                : data.detail;
        }

        throw new Error(message);
    }

    return data;
}


/* =========================================================
   LOGIN
========================================================= */

function showLogin(){

    document.getElementById("loginScreen").style.display = "flex";
    document.getElementById("app").style.display = "none";
}


function showApp(){

    document.getElementById("loginScreen").style.display = "none";
    document.getElementById("app").style.display = "flex";
}


async function login(username,password){

    const body =
        new URLSearchParams();

    body.append("username",username);
    body.append("password",password);

    const response = await fetch(
        API_BASE + "/auth/login",
        {
            method:"POST",
            headers:{
                "Content-Type":
                    "application/x-www-form-urlencoded"
            },
            body:body.toString()
        }
    );

    const data = await response.json();

    if(!response.ok){

        throw new Error(
            data.detail || "Invalid username or password"
        );
    }

    token = data.access_token;

    localStorage.setItem(
        "smart_mess_token",
        token
    );

    await loadProfile();

    showApp();

    showPage("dashboard");
}


document.getElementById("loginForm")
    .addEventListener("submit",async function(event){

        event.preventDefault();

        const username =
            document.getElementById("loginUsername").value.trim();

        const password =
            document.getElementById("loginPassword").value;

        const errorBox =
            document.getElementById("loginError");

        errorBox.style.display = "none";

        try{

            await login(username,password);

        }catch(error){

            errorBox.textContent = error.message;
            errorBox.style.display = "block";
        }

    });


document.getElementById("logoutBtn")
    .addEventListener("click",function(){

        localStorage.removeItem("smart_mess_token");
        token = null;

        showLogin();
    });


/* =========================================================
   NAVIGATION
========================================================= */

const pageTitles = {
    dashboard:"Dashboard",
    students:"Students",
    attendance:"Attendance",
    "student-profile":"Student Profile",
    menu:"Menu",
    consumption:"Consumption",
    waste:"Waste Record",
    analytics:"Analytics",
    reports:"Reports",
    profile:"Profile"
};


function showPage(page){

    document.querySelectorAll(".page")
        .forEach(section=>{
            section.classList.remove("active");
        });

    const section =
        document.getElementById("page-" + page);

    if(section){
        section.classList.add("active");
    }

    document.querySelectorAll(".nav-btn")
        .forEach(button=>{
            button.classList.remove("active");

            if(button.dataset.page === page){
                button.classList.add("active");
            }
        });

    document.getElementById("pageTitle").textContent =
        pageTitles[page] || "Smart Mess";


    if(page === "dashboard"){
        loadDashboard();
    }

    if(page === "students"){
        loadStudents();
    }

    if(page === "attendance"){
        loadTodayAttendance();
    }

    if(page === "menu"){
        loadMenuEditor();
    }

    if(page === "consumption"){
        loadConsumptionPage();
    }

    if(page === "waste"){
        loadWastePage();
    }

    if(page === "analytics"){
        loadAnalytics();
    }

    if(page === "reports"){
        prepareReports();
    }

    if(page === "profile"){
        loadProfilePage();
    }
}


document.querySelectorAll(".nav-btn")
    .forEach(button=>{

        button.addEventListener("click",()=>{

            showPage(button.dataset.page);

        });

    });



/* =========================================================
   ATTENDANCE
========================================================= */


/* =========================================================
   ANALYTICS
========================================================= */

async function loadAnalytics(){

    const alertBox =
        document.getElementById("analyticsAlert");

    try{

        const today = todayString();

        /* TODAY */

        const todayData = await api(
            `/analytics?from_date=${today}&to_date=${today}`
        );

        const preparedKg =
            Number(todayData.total_prepared_kg || 0);

        const servedKg =
            Number(todayData.total_served_kg || 0);

        const wasteKg =
            Number(todayData.total_waste_kg || 0);

        const preparedCount =
            Number(todayData.total_prepared_count || 0);

        const servedCount =
            Number(todayData.total_served_count || 0);

        const wasteCount =
            Number(todayData.total_waste_count || 0);

        const wastePercentageKg =
            Number(todayData.waste_percentage_kg || 0);

        const wastePercentageCount =
            Number(todayData.waste_percentage_count || 0);


        document.getElementById(
            "analyticsPrepared"
        ).innerHTML =
            `${preparedKg.toFixed(2)} kg<br>
             <small>${preparedCount.toFixed(2)} count</small>`;


        document.getElementById(
            "analyticsServed"
        ).innerHTML =
            `${servedKg.toFixed(2)} kg<br>
             <small>${servedCount.toFixed(2)} count</small>`;


        document.getElementById(
            "analyticsWaste"
        ).innerHTML =
            `${wasteKg.toFixed(2)} kg<br>
             <small>${wasteCount.toFixed(2)} count</small>`;


        document.getElementById(
            "analyticsPercentage"
        ).innerHTML =
            `${wastePercentageKg.toFixed(1)}% kg<br>
             <small>${wastePercentageCount.toFixed(1)}% count</small>`;


        /* WEEKLY: EXACTLY 7 DAYS */

        const todayDate =
            new Date(`${today}T00:00:00`);

        const weeklyStart =
            new Date(todayDate);

        weeklyStart.setDate(
            weeklyStart.getDate() - 6
        );

        const weeklyFrom =
            formatAnalyticsDate(weeklyStart);

        const weeklyData = await api(
            `/analytics?from_date=${weeklyFrom}&to_date=${today}`
        );

        let weeklyTrends =
            weeklyData.daily_trends || [];

        if(weeklyTrends.length > 7){
            weeklyTrends =
                weeklyTrends.slice(-7);
        }

        renderAnalyticsTrend(
            "weeklyTrendChart",
            weeklyTrends,
            "day"
        );


        /* MONTHLY */

        const rangeSelect =
            document.getElementById(
                "analyticsMonthRange"
            );

        const selectedDays =
            Number(rangeSelect?.value || 60);

        const monthlyStart =
            new Date(todayDate);

        monthlyStart.setDate(
            monthlyStart.getDate() -
            (selectedDays - 1)
        );

        const monthlyFrom =
            formatAnalyticsDate(monthlyStart);

        const monthlyData = await api(
            `/analytics?from_date=${monthlyFrom}&to_date=${today}`
        );

        const monthlyTrends =
            aggregateMonthlyWaste(
                monthlyData.daily_trends || []
            );

        renderAnalyticsTrend(
            "monthlyTrendChart",
            monthlyTrends,
            "month"
        );


        if(alertBox){
            alertBox.className = "alert";
            alertBox.textContent = "";
        }

    }
    catch(error){

        console.error(
            "Analytics error:",
            error
        );

        if(alertBox){

            alertBox.className = "alert error";

            alertBox.textContent =
                error.message ||
                "Unable to load analytics.";
        }


        const weekly =
            document.getElementById(
                "weeklyTrendChart"
            );

        const monthly =
            document.getElementById(
                "monthlyTrendChart"
            );


        if(weekly){
            weekly.innerHTML =
                `<div class="empty">
                    Unable to load weekly trend.
                 </div>`;
        }


        if(monthly){
            monthly.innerHTML =
                `<div class="empty">
                    Unable to load monthly trend.
                 </div>`;
        }

    }
}


/* DATE FORMAT */

function formatAnalyticsDate(date){

    const year =
        date.getFullYear();

    const month =
        String(
            date.getMonth() + 1
        ).padStart(2,"0");

    const day =
        String(
            date.getDate()
        ).padStart(2,"0");

    return `${year}-${month}-${day}`;
}


/* DAILY DATA -> MONTHLY TOTALS */

function aggregateMonthlyWaste(dailyData){

    const months = {};

    dailyData.forEach(item => {

        if(!item.date){
            return;
        }

        const monthKey =
            String(item.date).slice(0,7);

        if(!months[monthKey]){

            months[monthKey] = {
                date: monthKey,
                waste_kg: 0,
                waste_count: 0
            };

        }

        months[monthKey].waste_kg +=
            Number(item.waste_kg || 0);

        months[monthKey].waste_count +=
            Number(item.waste_count || 0);

    });

    return Object.values(months).sort(
        (a,b) =>
            a.date.localeCompare(b.date)
    );
}


/* TREND RENDERER */

function renderAnalyticsTrend(
    elementId,
    trends,
    type
){

    const container =
        document.getElementById(elementId);

    if(!container){
        return;
    }

    if(
        !Array.isArray(trends) ||
        trends.length === 0
    ){

        container.innerHTML =
            `<div class="empty">
                No waste data available for this period.
             </div>`;

        return;
    }


    const rows =
        trends.map(item => ({
            date:
                item.date || "",

            wasteKg:
                Number(item.waste_kg || 0),

            wasteCount:
                Number(item.waste_count || 0)
        }));


    const maxWasteKg =
        Math.max(
            ...rows.map(
                row => row.wasteKg
            ),
            1
        );


    container.innerHTML =
        rows.map(row => {

            let label = row.date;

            if(type === "month"){

                const parts =
                    row.date.split("-");

                const year =
                    parts[0];

                const month =
                    Number(parts[1]);

                const monthNames = [
                    "Jan","Feb","Mar","Apr",
                    "May","Jun","Jul","Aug",
                    "Sep","Oct","Nov","Dec"
                ];

                label =
                    `${monthNames[month - 1]} ${year}`;
            }


            const barHeight =
                Math.max(
                    3,
                    (
                        row.wasteKg /
                        maxWasteKg
                    ) * 100
                );


            return `
                <div class="trend-column">

                    <div class="trend-value">
                        ${row.wasteKg.toFixed(2)} kg
                    </div>

                    <div
                        class="trend-bar"
                        style="height:${barHeight}%"
                        title="${row.wasteKg.toFixed(2)} kg waste, ${row.wasteCount.toFixed(2)} count waste"
                    ></div>

                    <div class="trend-date">
                        ${escapeHtml(String(label))}
                    </div>

                </div>
            `;

        }).join("");
}


async function loadTodayAttendance(){

    const dateDisplay =
        document.getElementById("attendanceDateDisplay");

    const resultBox =
        document.getElementById("attendanceResult");

    const today =
        new Date();

    const dateText =
        today.toLocaleDateString(
            "en-IN",
            {
                day:"2-digit",
                month:"2-digit",
                year:"numeric"
            }
        );

    if(dateDisplay){
        dateDisplay.textContent =
            `Attendance Date: ${dateText}`;
    }

    try{

        const records =
            await api("/attendance/today");

        const attendance =
            Array.isArray(records)
                ? records
                : [];

        const uniqueStudents =
            new Set(
                attendance.map(
                    record => record.student_id
                )
            ).size;

        if(resultBox){

            if(attendance.length === 0){

                resultBox.innerHTML = `
                    <div class="alert alert-info">
                        No attendance has been recorded for today yet.
                    </div>
                `;

            }else{

                resultBox.innerHTML = `
                    <div class="alert alert-info">
                        Today's attendance:
                        <strong>${uniqueStudents}</strong>
                        student(s) attended,
                        with
                        <strong>${attendance.length}</strong>
                        meal attendance record(s).
                    </div>
                `;
            }
        }

        renderTodayAttendanceTable(attendance);

    }catch(error){

        if(resultBox){

            resultBox.innerHTML = `
                <div class="alert alert-error">
                    ${escapeHtml(error.message)}
                </div>
            `;
        }
    }
}


function renderTodayAttendanceTable(records){

    const container =
        document.getElementById(
            "todayAttendanceList"
        );

    if(!container){
        return;
    }

    if(!records.length){

        container.innerHTML = `
            <div class="empty">
                No attendance records for today.
            </div>
        `;

        return;
    }

    const rows =
        records.map(record => {

            const meal =
                String(record.meal || "")
                    .charAt(0)
                    .toUpperCase()
                +
                String(record.meal || "")
                    .slice(1);

            const scanTime =
                record.scan_time
                    ? new Date(
                        record.scan_time
                    ).toLocaleTimeString(
                        "en-IN",
                        {
                            hour:"2-digit",
                            minute:"2-digit"
                        }
                    )
                    : "—";

            return `
                <tr>
                    <td>${escapeHtml(
                        record.student_code || "—"
                    )}</td>

                    <td>${escapeHtml(
                        record.student_name || "—"
                    )}</td>

                    <td>${escapeHtml(meal)}</td>

                    <td>${escapeHtml(
                        scanTime
                    )}</td>

                    <td>
                        <span class="status-badge success">
                            Present
                        </span>
                    </td>
                </tr>
            `;
        }).join("");

    container.innerHTML = `
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Student ID</th>
                        <th>Student Name</th>
                        <th>Meal</th>
                        <th>Time</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>
                    ${rows}
                </tbody>
            </table>
        </div>
    `;
}


async function markAttendance(){

    const studentIdentifier =
        document
            .getElementById(
                "attendanceStudentId"
            )
            .value
            .trim();

    const meal =
        document
            .getElementById(
                "attendanceMeal"
            )
            .value;

    const resultBox =
        document.getElementById(
            "attendanceResult"
        );

    if(!studentIdentifier){

        resultBox.innerHTML = `
            <div class="alert alert-error">
                Please enter a Student ID or QR identifier.
            </div>
        `;

        return;
    }

    try{

        const data =
            await api(
                "/attendance/scan",
                {
                    method:"POST",
                    body:JSON.stringify({
                        student_identifier:
                            studentIdentifier,
                        meal:meal
                    })
                }
            );

        resultBox.innerHTML = `
            <div class="alert alert-success">
                Attendance marked successfully.
                <br>
                Meal:
                <strong>${escapeHtml(meal)}</strong>
                <br>
                Date:
                <strong>${new Date()
                    .toLocaleDateString(
                        "en-IN",
                        {
                            day:"2-digit",
                            month:"2-digit",
                            year:"numeric"
                        }
                    )}</strong>
            </div>
        `;

        document
            .getElementById(
                "attendanceStudentId"
            )
            .value = "";

        await loadTodayAttendance();

    }catch(error){

        resultBox.innerHTML = `
            <div class="alert alert-error">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}


async function simulateAttendance(){

    const count =
        Number(
            document
                .getElementById(
                    "simulateAttendanceCount"
                )
                .value
        );

    const meal =
        document
            .getElementById(
                "attendanceMeal"
            )
            .value;

    const resultBox =
        document.getElementById(
            "simulateAttendanceResult"
        );

    if(!count || count < 1){

        resultBox.innerHTML = `
            <div class="alert alert-error">
                Enter a valid student count.
            </div>
        `;

        return;
    }

    try{

        const query =
            new URLSearchParams({
                count:String(count),
                meal:meal
            });

        const data =
            await api(
                `/attendance/simulate?${query.toString()}`,
                {
                    method:"POST"
                }
            );

        resultBox.innerHTML = `
            <div class="alert alert-success">
                ${escapeHtml(data.message)}
                <br>
                Meal:
                <strong>${escapeHtml(
                    data.meal
                )}</strong>
                <br>
                Date:
                <strong>${escapeHtml(
                    data.date
                )}</strong>
            </div>
        `;

        await loadTodayAttendance();

    }catch(error){

        resultBox.innerHTML = `
            <div class="alert alert-error">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}


const markAttendanceButton =
    document.getElementById(
        "markAttendanceBtn"
    );

if(markAttendanceButton){

    markAttendanceButton.addEventListener(
        "click",
        markAttendance
    );
}


const simulateAttendanceButton =
    document.getElementById(
        "simulateAttendanceBtn"
    );

if(simulateAttendanceButton){

    simulateAttendanceButton.addEventListener(
        "click",
        simulateAttendance
    );
}


/* =========================================================
   PROFILE
========================================================= */

async function loadProfile(){

    try{

        currentUser =
            await api("/profile");

        const username =
            currentUser.username ||
            currentUser.name ||
            "User";

        document.getElementById("topUsername")
            .textContent = username;

        document.getElementById("topAvatar")
            .textContent =
            username.charAt(0).toUpperCase();

    }catch(error){

        console.error(error);

        currentUser = {
            username:"Warden",
            role:"warden"
        };

    }
}


async function loadProfilePage(){

    const box =
        document.getElementById("profileContent");

    try{

        const profile =
            currentUser || await api("/profile");

        box.innerHTML = `

            <div class="profile-header">

                <div class="profile-avatar">
                    ${escapeHtml(
                        (profile.username || "U")
                        .charAt(0)
                        .toUpperCase()
                    )}
                </div>

                <div>
                    <div class="profile-name">
                        ${escapeHtml(profile.username || "User")}
                    </div>

                    <div class="profile-id">
                        ${escapeHtml(profile.role || "Staff")}
                    </div>
                </div>

            </div>

            <div style="padding:0 20px 20px">

                <div class="detail-grid">

                    <div class="detail">
                        <div class="detail-label">Username</div>
                        <div class="detail-value">
                            ${escapeHtml(profile.username || "—")}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Role</div>
                        <div class="detail-value">
                            ${escapeHtml(profile.role || "—")}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Account</div>
                        <div class="detail-value">
                            Active
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">System</div>
                        <div class="detail-value">
                            Smart Mess
                        </div>
                    </div>

                </div>

            </div>
        `;

    }catch(error){

        box.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;

    }
}


/* =========================================================
   DASHBOARD
========================================================= */

async function loadDashboard(){

    document.getElementById("dashboardDate")
        .textContent =
        `Today's information — ${formatDate(todayString())}`;

    try{

        const data = await api("/dashboard");

        document.getElementById("statStudents")
            .textContent =
            data.total_students ?? "0";

        const waste =
            Number(data.total_waste_kg ?? 0);

        const prepared =
            Number(data.total_prepared_kg ?? 0);

        const percent =
            Number(data.today_waste_percentage ?? 0);

        document.getElementById("statWaste")
            .textContent =
            `${formatNumber(waste)} kg`;

        document.getElementById("statPrepared")
            .textContent =
            `${formatNumber(prepared)} kg`;

        document.getElementById("statWastePercent")
            .textContent =
            `${percent.toFixed(1)}%`;

        renderDashboardMenu(
            data.today_menu ||
            data.menu
        );

        renderDashboardAttendance(
            data.attendance ||
            []
        );

    }catch(error){

        console.error(error);

        loadTodayMenuFallback();
        loadTodayWasteFallback();
    }
}


function renderDashboardMenu(menu){

    const box =
        document.getElementById("dashboardMenu");

    if(!menu){

        box.innerHTML = `
            <div class="card meal-card">
                <div class="empty">
                    No menu has been saved for today.
                </div>
            </div>
        `;

        return;
    }

    currentMenu = menu;

    let html = "";

    const meals = [
        ["breakfast","Breakfast"],
        ["lunch","Lunch"],
        ["dinner","Dinner"]
    ];

    meals.forEach(([key,label])=>{

        let items = [];

        if(menu.items && Array.isArray(menu.items)){
            items =
                menu.items.filter(
                    item =>
                        String(item.meal || "").toLowerCase()
                        === key
                );
        }

        if(items.length === 0 && menu[key]){

            items =
                String(menu[key])
                .split(",")
                .map(item=>({
                    item_name:item.trim()
                }))
                .filter(item=>item.item_name);

        }

        html += `
            <div class="card meal-card">

                <div class="meal-name">
                    ${label}
                </div>

                <div class="menu-items">

                    ${
                        items.length
                        ? items.map(item=>`

                            <div class="menu-item">
                                <span>
                                    ${escapeHtml(
                                        item.item_name ||
                                        item.name ||
                                        ""
                                    )}
                                </span>
                            </div>

                        `).join("")
                        : `<div class="empty" style="padding:15px 0">
                            No items added
                           </div>`
                    }

                </div>

            </div>
        `;

    });

    box.innerHTML = html;
}


async function sendDashboardMenuNotification(){

    const result =
        document.getElementById("menuNotificationResult");

    if(!currentMenu || !currentMenu.date){

        result.innerHTML =
            `<div class="empty">
                No menu available to send.
             </div>`;

        return;
    }

    result.innerHTML =
        `<div class="loading">
            Sending menu notification...
         </div>`;

    try{

        const response =
            await api(
                `/menus/${currentMenu.date}/send-notification`,
                {
                    method: "POST"
                }
            );

        result.innerHTML = `
            <div class="success">
                📢 ${escapeHtml(
                    response.message ||
                    "Menu notification processed successfully."
                )}
            </div>
        `;

    }catch(error){

        console.error(error);

        result.innerHTML = `
            <div class="error">
                ❌ ${
                    escapeHtml(
                        error.message ||
                        "Failed to send menu notification."
                    )
                }
            </div>
        `;
    }
}


function renderDashboardAttendance(attendance){

    const box =
        document.getElementById("dashboardAttendance");

    const meals = [
        ["BREAKFAST","Breakfast"],
        ["LUNCH","Lunch"],
        ["DINNER","Dinner"]
    ];

    let html = "";

    meals.forEach(([key,label])=>{

        const item =
            Array.isArray(attendance)
                ? attendance.find(
                    x =>
                        String(x.meal)
                            .toUpperCase()
                        === key
                ) || {}
                : attendance[key] || {};

        const present =
            item.attended ??
            item.present ??
            item.present_count ??
            0;

        const skipped =
            item.skipped ??
            item.absent ??
            item.skipped_count ??
            0;

        const notYet =
            item.not_yet_attended ??
            item.not_attended ??
            item.pending ??
            0;

        html += `
            <div class="card meal-card">
                <div class="meal-name">
                    ${label}
                </div>

                <div class="meal-status-row">
                    <span>Attended</span>
                    <strong>${present}</strong>
                </div>

                <div class="meal-status-row">
                    <span>Not Yet Attended</span>
                    <strong>${notYet}</strong>
                </div>

                <div class="meal-status-row">
                    <span>Skipped</span>
                    <strong>${skipped}</strong>
                </div>
            </div>
        `;
    });

    box.innerHTML = html;
}

async function loadTodayMenuFallback(){

    try{

        const data =
            await api("/menus/today");

        renderDashboardMenu(data);

    }catch(error){

        renderDashboardMenu(null);

    }
}


async function loadTodayWasteFallback(){

    try{

        const data =
            await api("/waste/today-summary");

        const prepared =
            data.prepared_kg ||
            data.total_prepared ||
            0;

        const waste =
            data.waste_kg ||
            data.total_waste ||
            0;

        document.getElementById("statPrepared")
            .textContent =
            `${formatNumber(prepared)} kg`;

        document.getElementById("statWaste")
            .textContent =
            `${formatNumber(waste)} kg`;

        const percent =
            prepared > 0
            ? waste / prepared * 100
            : 0;

        document.getElementById("statWastePercent")
            .textContent =
            `${percent.toFixed(1)}%`;

    }catch(error){}
}


/* =========================================================
   WASTE
========================================================= */

async function loadWastePage(){

    const table =
        document.getElementById("wasteTable");

    table.innerHTML =
        `<div class="loading">Loading waste records...</div>`;

    try{

        await loadTodayWasteSummary();

        const records =
            await api("/waste");

        renderWasteRecords(
            Array.isArray(records)
                ? records
                : []
        );

    }catch(error){

        table.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;

    }
}


async function loadTodayWasteSummary(){

    try{

        const data =
            await api("/waste/today-summary");

        const preparedKg =
            Number(data.prepared_kg ?? 0);

        const servedKg =
            Number(data.served_kg ?? 0);

        const wasteKg =
            Number(data.waste_kg ?? 0);

        const preparedCount =
            Number(data.prepared_count ?? 0);

        const servedCount =
            Number(data.served_count ?? 0);

        const wasteCount =
            Number(data.waste_count ?? 0);

        const kgPercent =
            Number(data.waste_percentage_kg ?? 0);

        const countPercent =
            Number(data.waste_percentage_count ?? 0);

        const preparedParts = [];

        if(preparedKg > 0){
            preparedParts.push(
                `${formatNumber(preparedKg)} kg`
            );
        }

        if(preparedCount > 0){
            preparedParts.push(
                `${formatNumber(preparedCount)} count`
            );
        }

        const servedParts = [];

        if(servedKg > 0){
            servedParts.push(
                `${formatNumber(servedKg)} kg`
            );
        }

        if(servedCount > 0){
            servedParts.push(
                `${formatNumber(servedCount)} count`
            );
        }

        const wasteParts = [];

        if(wasteKg > 0){
            wasteParts.push(
                `${formatNumber(wasteKg)} kg`
            );
        }

        if(wasteCount > 0){
            wasteParts.push(
                `${formatNumber(wasteCount)} count`
            );
        }

        document.getElementById("wastePreparedToday")
            .textContent =
            preparedParts.length
                ? preparedParts.join(" + ")
                : "0";

        document.getElementById("wasteServedToday")
            .textContent =
            servedParts.length
                ? servedParts.join(" + ")
                : "0";

        document.getElementById("wasteToday")
            .textContent =
            wasteParts.length
                ? wasteParts.join(" + ")
                : "0";

        const percentParts = [];

        if(preparedKg > 0){
            percentParts.push(
                `${kgPercent.toFixed(1)}% kg`
            );
        }

        if(preparedCount > 0){
            percentParts.push(
                `${countPercent.toFixed(1)}% count`
            );
        }

        document.getElementById("wastePercentToday")
            .textContent =
            percentParts.length
                ? percentParts.join(" / ")
                : "0%";

    }catch(error){

        console.error(
            "Failed to load today's waste summary:",
            error
        );

        document.getElementById("wastePreparedToday")
            .textContent = "—";

        document.getElementById("wasteServedToday")
            .textContent = "—";

        document.getElementById("wasteToday")
            .textContent = "—";

        document.getElementById("wastePercentToday")
            .textContent = "—";
    }
}


function renderWasteRecords(records){

    const table =
        document.getElementById("wasteTable");

    const fromDate =
        document.getElementById("wasteFromDate")
            .value;

    const toDate =
        document.getElementById("wasteToDate")
            .value;

    const meal =
        document.getElementById("wasteMeal")
            .value;

    let filtered =
        records.filter(record => {

            const recordDate =
                String(record.date || "");

            if(fromDate && recordDate < fromDate){
                return false;
            }

            if(toDate && recordDate > toDate){
                return false;
            }

            if(
                meal &&
                String(record.meal || "").toLowerCase()
                !== meal.toLowerCase()
            ){
                return false;
            }

            return true;
        });

    if(!filtered.length){

        table.innerHTML = `
            <div class="empty">
                No waste records found for the selected filters.
            </div>
        `;

        return;
    }

    filtered.sort((a,b)=>{

        const dateCompare =
            String(b.date || "")
            .localeCompare(
                String(a.date || "")
            );

        if(dateCompare !== 0){
            return dateCompare;
        }

        return String(a.meal || "")
            .localeCompare(
                String(b.meal || "")
            );

    });

    table.innerHTML = `

        <table>

            <thead>

                <tr>
                    <th>Date</th>
                    <th>Meal</th>
                    <th>Item</th>
                    <th>Prepared</th>
                    <th>Served</th>
                    <th>Waste</th>
                    <th>Unit</th>
                </tr>

            </thead>

            <tbody>

                ${filtered.map(record => {

                    const unit =
                        String(record.unit || "kg")
                        .toLowerCase();

                    const unitLabel =
                        unit === "count"
                            ? "Count"
                            : "Kg";

                    return `

                        <tr>

                            <td>
                                ${escapeHtml(
                                    formatDate(
                                        record.date
                                    )
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    capitalize(
                                        record.meal || "—"
                                    )
                                )}
                            </td>

                            <td>
                                <strong>
                                    ${escapeHtml(
                                        record.item_name || "—"
                                    )}
                                </strong>
                            </td>

                            <td>
                                ${formatNumber(
                                    Number(
                                        record.prepared_kg || 0
                                    )
                                )}
                            </td>

                            <td>
                                ${formatNumber(
                                    Number(
                                        record.served_kg || 0
                                    )
                                )}
                            </td>

                            <td>
                                <strong>
                                    ${formatNumber(
                                        Number(
                                            record.waste_kg || 0
                                        )
                                    )}
                                </strong>
                            </td>

                            <td>
                                ${unitLabel}
                            </td>

                        </tr>

                    `;

                }).join("")}

            </tbody>

        </table>
    `;
}


document.getElementById("wasteFilterBtn")
    .addEventListener("click", async ()=>{

        const table =
            document.getElementById("wasteTable");

        table.innerHTML =
            `<div class="loading">Loading waste records...</div>`;

        try{

            const records =
                await api("/waste");

            renderWasteRecords(
                Array.isArray(records)
                    ? records
                    : []
            );

        }catch(error){

            table.innerHTML =
                `<div class="empty">${escapeHtml(error.message)}</div>`;

        }

    });


document.getElementById("wasteClearBtn")
    .addEventListener("click", ()=>{

        document.getElementById("wasteFromDate")
            .value = "";

        document.getElementById("wasteToDate")
            .value = "";

        document.getElementById("wasteMeal")
            .value = "";

        loadWastePage();

    });


/* =========================================================
   STUDENTS
========================================================= */

async function loadStudents(search=""){

    const box =
        document.getElementById("studentsTable");

    box.innerHTML =
        `<div class="loading">Loading students...</div>`;

    try{

        let url = "/students";

        if(search.trim()){
            url +=
                `?search=${encodeURIComponent(search.trim())}`;
        }

        const data =
            await api(url);

        currentStudents =
            Array.isArray(data)
                ? data
                : data.students || [];

        renderStudents(currentStudents);

    }catch(error){

        box.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;

    }
}


function renderStudents(students){

    const box =
        document.getElementById("studentsTable");

    document.getElementById("studentCount")
        .textContent =
        `(${students.length})`;

    if(!students.length){

        box.innerHTML = `
            <div class="empty">
                No students found.
            </div>
        `;

        return;
    }

    box.innerHTML = `

        <table>

            <thead>
                <tr>
                    <th>Student ID</th>
                    <th>Name</th>
                    <th>Roll Number</th>
                    <th>Department</th>
                    <th>Year</th>
                    <th>Block</th>
                    <th>Room</th>
                </tr>
            </thead>

            <tbody>

                ${students.map(student=>`

                    <tr
                        class="clickable"
                        onclick="openStudentProfile(${student.id})"
                    >

                        <td>
                            <strong>
                                ${escapeHtml(
                                    student.student_code ||
                                    student.student_id ||
                                    "—"
                                )}
                            </strong>
                        </td>

                        <td>
                            ${escapeHtml(student.name || "—")}
                        </td>

                        <td>
                            ${escapeHtml(
                                student.roll_number || "—"
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                student.department || "—"
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                student.year || "—"
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                student.block || "—"
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                student.room_number || "—"
                            )}
                        </td>

                    </tr>

                `).join("")}

            </tbody>

        </table>
    `;
}


document.getElementById("studentSearchBtn")
    .addEventListener("click",()=>{

        loadStudents(
            document.getElementById("studentSearch").value
        );

    });


document.getElementById("studentSearch")
    .addEventListener("keydown",event=>{

        if(event.key === "Enter"){

            loadStudents(
                document.getElementById("studentSearch").value
            );

        }

    });


document.getElementById("studentClearBtn")
    .addEventListener("click",()=>{

        document.getElementById("studentSearch").value = "";

        loadStudents();

    });


async function openStudentProfile(studentId){

    showPage("student-profile");

    const box =
        document.getElementById("studentProfileContent");

    box.innerHTML =
        `<div class="loading">Loading student profile...</div>`;

    try{

        const student =
            await api(`/students/${studentId}`);

        renderStudentProfile(student);

    }catch(error){

        box.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;

    }
}


function renderStudentProfile(response){

    const box =
        document.getElementById("studentProfileContent");

    const student =
        response.student || response;

    const initials =
        (student.name || "S")
        .split(" ")
        .map(x=>x.charAt(0))
        .join("")
        .substring(0,2)
        .toUpperCase();

    const history =
        response.history ||
        student.attendance_history ||
        student.history ||
        student.meal_history ||
        [];

    box.innerHTML = `

        <div class="card">

            <div class="profile-header">

                <div class="profile-avatar">
                    ${escapeHtml(initials)}
                </div>

                <div>

                    <div class="profile-name">
                        ${escapeHtml(student.name || "—")}
                    </div>

                    <div class="profile-id">
                        Student ID:
                        ${escapeHtml(
                            student.student_code ||
                            student.student_id ||
                            "—"
                        )}
                    </div>

                </div>

            </div>


            <div style="padding:0 20px 20px">

                <div class="detail-grid">

                    <div class="detail">
                        <div class="detail-label">Student ID</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.student_code ||
                                student.student_id ||
                                "—"
                            )}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Roll Number</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.roll_number || "—"
                            )}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Department</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.department || "—"
                            )}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Year</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.year || "—"
                            )}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Block</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.block || "—"
                            )}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Room</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.room_number || "—"
                            )}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">Phone</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.phone_number || "—"
                            )}
                        </div>
                    </div>

                    <div class="detail">
                        <div class="detail-label">QR Identifier</div>
                        <div class="detail-value">
                            ${escapeHtml(
                                student.qr_token || "Assigned"
                            )}
                        </div>
                    </div>

                </div>

            </div>

        </div>


        <div class="card" style="margin-top:15px">

            <div class="card-header">
                <div class="card-title">
                    Meal History
                </div>
            </div>

            ${
                history.length
                ? `

                    <div class="table-wrap">

                        <table>

                            <thead>

                                <tr>
                                    <th>Date</th>
                                    <th>Meal</th>
                                    <th>Status</th>
                                    <th>Scan Time</th>
                                </tr>

                            </thead>

                            <tbody>

                                ${history.map(record=>`

                                    <tr>

                                        <td>
                                            ${formatDate(
                                                record.date
                                            )}
                                        </td>

                                        <td>
                                            ${capitalize(
                                                record.meal
                                            )}
                                        </td>

                                        <td>
                                            ${
                                                String(
                                                    record.status || ""
                                                ).toLowerCase()
                                                === "present"
                                                ? `<span class="badge badge-green">Present</span>`
                                                : `<span class="badge badge-red">Skipped</span>`
                                            }
                                        </td>

                                        <td>
                                            ${escapeHtml(
                                                record.scan_time ||
                                                record.time ||
                                                "—"
                                            )}
                                        </td>

                                    </tr>

                                `).join("")}

                            </tbody>

                        </table>

                    </div>

                `
                : `
                    <div class="empty">
                        No meal history available.
                    </div>
                `
            }

        </div>
    `;
}


/* =========================================================
   MENU
========================================================= */

function loadMenuEditor(){

    const dateInput =
        document.getElementById("menuDate");

    dateInput.value =
        dateInput.value || todayString();

    const container =
        document.getElementById("menuEditors");

    container.innerHTML = "";

    const meals = [
        ["breakfast", "Breakfast"],
        ["lunch", "Lunch"],
        ["dinner", "Dinner"]
    ];

    meals.forEach(([meal, label]) => {

        container.innerHTML += `
            <div
                class="meal-editor"
                data-meal="${meal}"
            >

                <div class="meal-editor-header">
                    <span>${label}</span>
                </div>

                <div class="items-container"></div>

                <button
                    type="button"
                    class="btn btn-secondary btn-small add-item"
                    onclick="addMenuItem('${meal}')"
                >
                    + Add Item
                </button>

            </div>
        `;

    });

    meals.forEach(([meal]) => {
        addMenuItem(meal);
    });

    loadExistingMenuForDate();
}


function addMenuItem(meal){

    const editor =
        document.querySelector(
            `.meal-editor[data-meal="${meal}"]`
        );

    if(!editor){
        return;
    }

    const container =
        editor.querySelector(".items-container");

    const row =
        document.createElement("div");

    row.className = "item-row";

    row.innerHTML = `
        <input
            type="text"
            class="menu-item-name"
            placeholder="Item name"
        >

        <input
            type="number"
            class="menu-item-servings"
            min="1"
            step="1"
            placeholder="Quantity"
        >

        <select class="menu-item-unit">
            <option value="kg">Kg</option>
            <option value="count">Count</option>
        </select>

        <button
            type="button"
            class="remove-item"
            onclick="this.parentElement.remove()"
        >
            ×
        </button>
    `;

    container.appendChild(row);

    row.querySelector(".menu-item-name").focus();
}


async function loadExistingMenuForDate(){

    const date =
        document.getElementById("menuDate").value;

    if(!date){
        return;
    }

    try{

        const data =
            await api(`/menus?date=${date}`);

        const menu =
            Array.isArray(data)
                ? data[0]
                : data;

        if(!menu){
            return;
        }

        existingMenuData = menu;

        showExistingAllMeals();

    }catch(error){

        console.log(
            "No existing menu",
            error.message
        );

    }
}


function showExistingAllMeals(){

    if(!existingMenuData){
        return;
    }

    const meals = [
        "breakfast",
        "lunch",
        "dinner"
    ];

    meals.forEach(meal => {

        const editor =
            document.querySelector(
                `.meal-editor[data-meal="${meal}"]`
            );

        if(!editor){
            return;
        }

        const container =
            editor.querySelector(".items-container");

        if(!container){
            return;
        }

        container.innerHTML = "";

        let items = [];

        if(Array.isArray(existingMenuData.items)){

            items =
                existingMenuData.items.filter(
                    item =>
                        String(item.meal).toLowerCase()
                        === meal
                );
        }

        if(items.length === 0 && existingMenuData[meal]){

            items =
                String(existingMenuData[meal])
                .split(",")
                .map(name => ({
                    item_name: name.trim(),
                    planned_servings: 1,
                    unit: "kg"
                }))
                .filter(x => x.item_name);
        }

        if(items.length === 0){
            addMenuItem(meal);
            return;
        }

        items.forEach(item => {

            const unit =
                item.unit === "count"
                    ? "count"
                    : "kg";

            const row =
                document.createElement("div");

            row.className = "item-row";

            row.innerHTML = `
                <input
                    type="text"
                    class="menu-item-name"
                    value="${escapeHtml(
                        item.item_name || ""
                    )}"
                    placeholder="Item name"
                >

                <input
                    type="number"
                    class="menu-item-servings"
                    min="1"
                    step="${unit === "count" ? "1" : "0.01"}"
                    value="${item.planned_servings ?? 1}"
                    placeholder="Quantity"
                >

                <select class="menu-item-unit">
                    <option value="kg" ${unit === "kg" ? "selected" : ""}>Kg</option>
                    <option value="count" ${unit === "count" ? "selected" : ""}>Count</option>
                </select>

                <button
                    type="button"
                    class="remove-item"
                    onclick="this.parentElement.remove()"
                >
                    ×
                </button>
            `;

            container.appendChild(row);

            const quantityInput =
                row.querySelector(".menu-item-servings");

            const unitSelect =
                row.querySelector(".menu-item-unit");

            unitSelect.addEventListener("change", () => {

                if(unitSelect.value === "count"){
                    quantityInput.step = "1";
                    quantityInput.value =
                        String(
                            Math.max(
                                1,
                                Math.round(
                                    Number(quantityInput.value) || 1
                                )
                            )
                        );
                }else{
                    quantityInput.step = "0.01";
                }

            });

        });

    });
}


let existingMenuData = null;


document.getElementById("menuDate")
    .addEventListener(
        "change",
        loadMenuEditor
    );


document.getElementById("saveMenuBtn")
    .addEventListener(
        "click",
        saveMenu
    );


async function saveMenu(){

    const date =
        document.getElementById("menuDate").value;

    if(!date){

        showToast(
            "Please select a menu date.",
            true
        );

        return;
    }

    const meals = [];

    let validationError = "";

    document.querySelectorAll(".meal-editor")
        .forEach(editor => {

            const meal =
                editor.dataset.meal;

            const items = [];

            editor.querySelectorAll(".item-row")
                .forEach(row => {

                    const name =
                        row.querySelector(".menu-item-name")
                        .value.trim();

                    const quantity =
                        Number(
                            row.querySelector(
                                ".menu-item-servings"
                            ).value || 0
                        );

                    const unit =
                        row.querySelector(
                            ".menu-item-unit"
                        ).value;

                    if(!name){
                        return;
                    }

                    if(quantity <= 0){
                        validationError =
                            `${meal.charAt(0).toUpperCase() + meal.slice(1)}: quantity must be greater than 0.`;
                        return;
                    }

                    if(
                        unit === "count"
                        && !Number.isInteger(quantity)
                    ){
                        validationError =
                            `${name}: count-based items must use a whole number.`;
                        return;
                    }

                    items.push({
                        item_name:name,
                        planned_servings:quantity,
                        unit:unit
                    });

                });

            if(items.length === 0){

                if(!validationError){
                    validationError =
                        `${meal.charAt(0).toUpperCase() + meal.slice(1)} must contain at least one item.`;
                }

                return;
            }

            meals.push({
                meal:meal,
                items:items
            });

        });

    if(validationError){

        showToast(
            validationError,
            true
        );

        return;
    }

    const mealNames =
        meals.map(meal => meal.meal);

    const requiredMeals =
        ["breakfast", "lunch", "dinner"];

    const hasAllMeals =
        requiredMeals.every(
            meal => mealNames.includes(meal)
        );

    if(
        meals.length !== 3
        || !hasAllMeals
    ){

        showToast(
            "Breakfast, Lunch and Dinner must each contain at least one item.",
            true
        );

        return;
    }

    try{

        await api(
            "/menus",
            {
                method:"POST",
                body:JSON.stringify({
                    date:date,
                    meals:meals
                })
            }
        );

        showToast(
            "Menu saved successfully."
        );

        existingMenuData = null;

        if(date === todayString()){
            loadDashboard();
        }

        loadMenuEditor();

    }catch(error){

        showToast(
            error.message || "Failed to save menu.",
            true
        );

    }

}


/* =========================================================
   REPORTS
========================================================= */

let currentReportData = null;


function getReportDates(){

    const fromDate =
        document.getElementById("reportFrom").value;

    const toDate =
        document.getElementById("reportTo").value;

    if(!fromDate || !toDate){

        showToast(
            "Please select both From Date and To Date.",
            true
        );

        return null;
    }

    if(fromDate > toDate){

        showToast(
            "From Date cannot be after To Date.",
            true
        );

        return null;
    }

    return {
        from_date: fromDate,
        to_date: toDate
    };
}


function renderReport(reportData){

    const container =
        document.getElementById("reportResult");

    if(!container){
        return;
    }

    currentReportData = reportData;

    const summary =
        reportData.waste_summary || {};

    const report =
        reportData.report || {};

    const items =
        reportData.item_breakdown || [];

    const attendance =
        reportData.attendance_summary || {};


    const kgPrepared =
        Number(summary.total_prepared_kg || 0);

    const kgServed =
        Number(summary.total_served_kg || 0);

    const kgWaste =
        Number(summary.total_waste_kg || 0);

    const kgWastePercentage =
        Number(summary.waste_percentage_kg || 0);


    const countPrepared =
        Number(summary.total_prepared_count || 0);

    const countServed =
        Number(summary.total_served_count || 0);

    const countWaste =
        Number(summary.total_waste_count || 0);

    const countWastePercentage =
        Number(summary.waste_percentage_count || 0);


    let itemRows = "";

    if(items.length === 0){

        itemRows = `
            <tr>
                <td colspan="5" style="text-align:center;">
                    No consumption records found for this period.
                </td>
            </tr>
        `;

    }else{

        itemRows = items.map(item => {

            const unit =
                String(item.unit || "kg").toLowerCase();

            const unitLabel =
                unit === "count" ? "Count" : "Kg";

            return `
                <tr>
                    <td>${escapeHtml(item.item_name)}</td>
                    <td>${unitLabel}</td>
                    <td>${formatNumber(item.prepared)}</td>
                    <td>${formatNumber(item.served)}</td>
                    <td>${formatNumber(item.waste)}</td>
                </tr>
            `;

        }).join("");

    }


    container.innerHTML = `

        <div id="printableReport" class="card">

            <div class="card-body">

                <div
                    style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        gap:10px;
                        flex-wrap:wrap;
                    "
                >

                    <div>
                        <h2 style="margin:0;">
                            Mess Performance Report
                        </h2>

                        <p style="margin:6px 0 0;">
                            ${formatDate(report.from_date)}
                            to
                            ${formatDate(report.to_date)}
                        </p>
                    </div>

                    <button
                        id="printReportBtn"
                        class="btn btn-secondary"
                        type="button"
                    >
                        🖨️ Print Report
                    </button>

                </div>


                <hr style="margin:18px 0;">


                <h3>Waste Summary</h3>

                <div class="filter-row">

                    <div class="card">
                        <div class="card-body">

                            <strong>Weight (Kg)</strong>

                            <p>
                                Prepared:
                                <strong>
                                    ${formatNumber(kgPrepared)} kg
                                </strong>
                            </p>

                            <p>
                                Served:
                                <strong>
                                    ${formatNumber(kgServed)} kg
                                </strong>
                            </p>

                            <p>
                                Waste:
                                <strong>
                                    ${formatNumber(kgWaste)} kg
                                </strong>
                            </p>

                            <p>
                                Waste %:
                                <strong>
                                    ${formatNumber(kgWastePercentage)}%
                                </strong>
                            </p>

                        </div>
                    </div>


                    <div class="card">
                        <div class="card-body">

                            <strong>Count (Items)</strong>

                            <p>
                                Prepared:
                                <strong>
                                    ${formatNumber(countPrepared)}
                                </strong>
                            </p>

                            <p>
                                Served:
                                <strong>
                                    ${formatNumber(countServed)}
                                </strong>
                            </p>

                            <p>
                                Waste:
                                <strong>
                                    ${formatNumber(countWaste)}
                                </strong>
                            </p>

                            <p>
                                Waste %:
                                <strong>
                                    ${formatNumber(countWastePercentage)}%
                                </strong>
                            </p>

                        </div>
                    </div>

                </div>


                <h3 style="margin-top:25px;">
                    Attendance Summary
                </h3>

                <div class="card">
                    <div class="card-body">

                        <p>
                            Attended Meals:
                            <strong>
                                ${Number(attendance.attended_meals || 0)}
                            </strong>
                        </p>

                        <p>
                            Skipped Meals:
                            <strong>
                                ${Number(attendance.skipped_meals || 0)}
                            </strong>
                        </p>

                    </div>
                </div>


                <h3 style="margin-top:25px;">
                    Item-wise Breakdown
                </h3>

                <div style="overflow-x:auto;">

                    <table
                        style="
                            width:100%;
                            border-collapse:collapse;
                        "
                    >

                        <thead>

                            <tr>

                                <th
                                    style="
                                        text-align:left;
                                        padding:10px;
                                    "
                                >
                                    Item
                                </th>

                                <th
                                    style="
                                        text-align:left;
                                        padding:10px;
                                    "
                                >
                                    Unit
                                </th>

                                <th
                                    style="
                                        text-align:right;
                                        padding:10px;
                                    "
                                >
                                    Prepared
                                </th>

                                <th
                                    style="
                                        text-align:right;
                                        padding:10px;
                                    "
                                >
                                    Served
                                </th>

                                <th
                                    style="
                                        text-align:right;
                                        padding:10px;
                                    "
                                >
                                    Waste
                                </th>

                            </tr>

                        </thead>

                        <tbody>

                            ${itemRows}

                        </tbody>

                    </table>

                </div>

            </div>

        </div>

    `;


    const printButton =
        document.getElementById("printReportBtn");

    if(printButton){

        printButton.addEventListener(
            "click",
            printReport
        );

    }

}


async function generateReport(){

    const dates = getReportDates();

    if(!dates){
        return;
    }


    const button =
        document.getElementById("generateReportBtn");

    const result =
        document.getElementById("reportResult");


    try{

        if(button){
            button.disabled = true;
            button.textContent = "Generating...";
        }

        if(result){

            result.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        Generating report...
                    </div>
                </div>
            `;

        }


        const data =
            await api(
                "/reports/generate",
                {
                    method:"POST",
                    body:JSON.stringify(dates)
                }
            );


        renderReport(data);

        showToast(
            "Report generated successfully."
        );


    }catch(error){

        if(result){

            result.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <strong>
                            Failed to generate report
                        </strong>
                        <p>
                            ${escapeHtml(
                                error.message ||
                                "Unable to generate report."
                            )}
                        </p>
                    </div>
                </div>
            `;

        }

        showToast(
            error.message ||
            "Failed to generate report.",
            true
        );

    }finally{

        if(button){

            button.disabled = false;
            button.textContent = "Generate Report";

        }

    }

}


async function downloadReport(){

    const dates = getReportDates();

    if(!dates){
        return;
    }


    const button =
        document.getElementById("downloadReportBtn");


    try{

        if(button){

            button.disabled = true;
            button.textContent = "Downloading...";

        }


        const response =
            await fetch(
                API_BASE + "/reports/download",
                {
                    method:"POST",

                    headers:{
                        "Authorization":
                            `Bearer ${token}`,

                        "Content-Type":
                            "application/json"
                    },

                    body:JSON.stringify(dates)
                }
            );


        if(response.status === 401){

            localStorage.removeItem(
                "smart_mess_token"
            );

            token = null;

            showLogin();

            throw new Error(
                "Session expired. Please login again."
            );

        }


        if(!response.ok){

            let message =
                "Failed to download report.";

            try{

                const errorData =
                    await response.json();

                message =
                    errorData.detail ||
                    message;

            }catch(_){

                // Keep default message.

            }

            throw new Error(message);

        }


        const blob =
            await response.blob();


        const url =
            window.URL.createObjectURL(blob);


        const link =
            document.createElement("a");

        link.href = url;

        link.download =
            `smart_mess_report_${dates.from_date}_to_${dates.to_date}.pdf`;

        document.body.appendChild(link);

        link.click();

        link.remove();

        window.URL.revokeObjectURL(url);


        showToast(
            "Report PDF downloaded successfully."
        );


    }catch(error){

        showToast(
            error.message ||
            "Failed to download report.",
            true
        );

    }finally{

        if(button){

            button.disabled = false;
            button.textContent = "📥 Download Report";

        }

    }

}


function printReport(){

    const report =
        document.getElementById("printableReport");

    if(!report){

        showToast(
            "Generate a report before printing.",
            true
        );

        return;

    }


    const printWindow =
        window.open(
            "",
            "_blank",
            "width=1000,height=800"
        );


    if(!printWindow){

        showToast(
            "Please allow pop-ups to print the report.",
            true
        );

        return;

    }


    printWindow.document.write(`

        <!DOCTYPE html>

        <html>

        <head>

            <title>Smart Mess Report</title>

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1"
            >

            <style>

                body{
                    font-family:Arial,sans-serif;
                    padding:30px;
                    color:#222;
                }

                h2,h3{
                    margin-bottom:8px;
                }

                p{
                    margin:6px 0;
                }

                table{
                    width:100%;
                    border-collapse:collapse;
                    margin-top:10px;
                }

                th,
                td{
                    border:1px solid #999;
                    padding:8px;
                }

                th{
                    text-align:left;
                }

                .card{
                    border:1px solid #ccc;
                    padding:15px;
                    margin-bottom:15px;
                }

                button{
                    display:none;
                }

                hr{
                    border:none;
                    border-top:1px solid #aaa;
                }

            </style>

        </head>

        <body>

            ${report.innerHTML}

        </body>

        </html>

    `);


    printWindow.document.close();

    printWindow.focus();


    setTimeout(
        ()=>{
            printWindow.print();
            printWindow.close();
        },
        300
    );

}


async function loadConsumptionPage(){

    const dateInput =
        document.getElementById("consumptionDate");

    dateInput.value =
        dateInput.value || todayString();

    await loadConsumptionItems();

    await loadConsumptionRecords();

}


async function loadConsumptionItems(){

    const date =
        document.getElementById("consumptionDate").value;

    const meal =
        document.getElementById("consumptionMeal").value;

    const select =
        document.getElementById("consumptionItem");

    select.innerHTML =
        `<option value="">Loading...</option>`;

    try{

        const data =
            await api(`/menus?date=${date}`);

        const menu =
            Array.isArray(data)
                ? data[0]
                : data;

        if(!menu || !menu.items){

            select.innerHTML =
                `<option value="">No menu items</option>`;

            return;
        }

        const items =
            menu.items.filter(
                item =>
                    String(item.meal).toLowerCase()
                    === meal
            );

        select.innerHTML =
            `<option value="">Select item</option>` +
            items.map(item=>`

                <option
                    value="${item.id}"
                    data-name="${escapeHtml(item.item_name)}"
                >
                    ${escapeHtml(item.item_name)}
                </option>

            `).join("");

    }catch(error){

        select.innerHTML =
            `<option value="">No menu items</option>`;

    }
}


document.getElementById("consumptionDate")
    .addEventListener("change",loadConsumptionItems);

document.getElementById("consumptionMeal")
    .addEventListener("change",loadConsumptionItems);


document.getElementById("saveConsumptionBtn")
    .addEventListener("click",saveConsumption);


async function saveConsumption(){

    const date =
        document.getElementById("consumptionDate").value;

    const meal =
        document.getElementById("consumptionMeal").value;

    const itemSelect =
        document.getElementById("consumptionItem");

    const itemId =
        itemSelect.value;

    const selectedOption =
        itemSelect.options[itemSelect.selectedIndex];

    const itemName =
        selectedOption?.dataset?.name ||
        selectedOption?.textContent?.trim() ||
        "";

    const prepared =
        Number(
            document.getElementById("preparedKg").value
        );

    const served =
        Number(
            document.getElementById("servedKg").value
        );

    if(!date || !itemId || !itemName){

        showToast(
            "Please select date, meal and menu item.",
            true
        );

        return;
    }

    if(
        Number.isNaN(prepared) ||
        Number.isNaN(served) ||
        prepared < 0 ||
        served < 0
    ){

        showToast(
            "Enter valid prepared and served quantities.",
            true
        );

        return;
    }

    if(served > prepared){

        showToast(
            "Served quantity cannot exceed prepared quantity.",
            true
        );

        return;
    }

    try{

        await api(
            "/consumption",
            {
                method:"POST",
                body:JSON.stringify({
                    date:date,
                    meal:meal,
                    item_name:itemName,
                    prepared_kg:prepared,
                    served_kg:served,
                    menu_item_id:Number(itemId)
                })
            }
        );

        showToast(
            "Consumption saved successfully."
        );

        document.getElementById("preparedKg").value = "";
        document.getElementById("servedKg").value = "";

        await loadConsumptionRecords();

        if(date === todayString()){
            loadDashboard();
            loadWastePage();
        }

    }catch(error){

        showToast(
            error.message,
            true
        );

    }
}


async function loadConsumptionRecords(){

    const box =
        document.getElementById("consumptionTable");

    box.innerHTML =
        `<div class="loading">Loading consumption records...</div>`;

    try{

        const data =
            await api("/consumption");

        const records =
            Array.isArray(data)
                ? data
                : data.records || [];

        if(!records.length){

            box.innerHTML =
                `<div class="empty">No consumption records found.</div>`;

            return;
        }

        box.innerHTML = `

            <table>

                <thead>

                    <tr>
                        <th>Date</th>
                        <th>Meal</th>
                        <th>Item</th>
                        <th>Prepared</th>
                        <th>Served</th>
                        <th>Waste</th>
                    </tr>

                </thead>

                <tbody>

                    ${records.map(record=>`

                        <tr>

                            <td>
                                ${formatDate(record.date)}
                            </td>

                            <td>
                                ${capitalize(record.meal)}
                            </td>

                            <td>
                                ${escapeHtml(record.item_name)}
                            </td>

                            <td>
                                ${formatNumber(record.prepared_kg)} kg
                            </td>

                            <td>
                                ${formatNumber(record.served_kg)} kg
                            </td>

                            <td>
                                <strong>
                                    ${formatNumber(record.waste_kg)} kg
                                </strong>
                            </td>

                        </tr>

                    `).join("")}

                </tbody>

            </table>
        `;

    }catch(error){

        box.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;

    }
}

/* =========================================================
   REPORT EVENT LISTENERS
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    ()=>{
        
        const generateButton =
            document.getElementById(
                "generateReportBtn"
            );

        const downloadButton =
            document.getElementById(
                "downloadReportBtn"
            );


        if(generateButton){

            generateButton.addEventListener(
                "click",
                generateReport
            );

        }


        if(downloadButton){

            downloadButton.addEventListener(
                "click",
                downloadReport
            );

        }

    }
);

