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


let countdown = setInterval(()=>{

    time--;

    timer.innerText = `Resend available in ${time}s`;

    if(time <=0){

        clearInterval(countdown);

        timer.innerText="You can resend OTP now";
        resendBtn.disabled=false;

    }

},1000);



document.getElementById("verifyBtn").addEventListener("click",()=>{

    let otp="";

    inputs.forEach(input=>{
        otp += input.value;
    });


    if(otp.length !== 6){
        alert("Please enter 6 digit OTP");
        return;
    }


    alert("OTP Verified Successfully!");

});