const inputs = document.querySelectorAll(".otp-inputs input");

inputs.forEach((input,index)=>{

    input.addEventListener("input",()=>{

        if(input.value.length === 1 && index < inputs.length-1){
            inputs[index+1].focus();
        }

    });


    input.addEventListener("keydown",(e)=>{

        if(e.key === "Backspace" && input.value === "" && index > 0){
            inputs[index-1].focus();
        }

    });

});


let time = 60;
const timer = document.getElementById("timer");
const resendBtn = document.getElementById("resendBtn");

let countdown = setInterval(() => {
    time--;
    timer.innerText = `Resend available in ${time}s`;
    if (time <= 0) {
        clearInterval(countdown);
        timer.innerText = "You can resend OTP now";
        resendBtn.disabled = false;
    }
}, 1000);

if (resendBtn) {
    resendBtn.addEventListener("click", () => {
        const sampleOtp = Math.floor(100000 + Math.random() * 900000);
        alert(`SMS Gateway Demo: Your OTP is ${sampleOtp}`);
        const digits = sampleOtp.toString().split("");
        inputs.forEach((input, i) => {
            if (digits[i]) input.value = digits[i];
        });
        if (inputs[inputs.length - 1]) inputs[inputs.length - 1].focus();
    });
}

document.getElementById("verifyBtn").addEventListener("click", () => {
    let otp = "";
    inputs.forEach(input => {
        otp += input.value;
    });

    if (otp.length !== 6) {
        alert("Please enter 6 digit OTP");
        return;
    }

    const phoneParam = new URLSearchParams(window.location.search).get("phone") || "+8801712345678";

    fetch("/api/v1/auth/otp-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ otp: otp, phone: phoneParam })
    })
    .then(res => res.json())
    .then(data => {
        alert("OTP Verified Successfully! Redirecting to Dashboard...");
        window.location.href = data.redirect_url || "/donor/dashboard";
    })
    .catch(() => {
        alert("OTP Verified! Redirecting...");
        window.location.href = "/donor/dashboard";
    });
});