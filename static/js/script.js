document.getElementById('register-button').addEventListener('click', () => {
    document.getElementById('main-form').classList.add('hidden');
    document.getElementById('register-widget').classList.remove('hidden');
});

document.getElementById('validation-button').addEventListener('click', () => {
    document.getElementById('main-form').classList.add('hidden');
    document.getElementById('validation-widget').classList.remove('hidden');
});

function saveChemical() {
    const name = document.getElementById('associate-name').value;
    const vendor = document.getElementById('vendor-name').value;
    const description = document.getElementById('chemical-description').value;
    const batch = document.getElementById('batch-name').value;
    const expiry = document.getElementById('expiry-date').value;

    fetch('/save-chemical', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, vendor, description, batch, expiry })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('qr-code').innerHTML = `<img src="${data.qr_code}" alt="QR Code">`;
    });
}

function validateChemical() {
    const input = document.getElementById('barcode-input').files[0];
    const reader = new FileReader();

    reader.onload = function(event) {
        const imageData = event.target.result;
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const image = new Image();
        
        image.onload = function() {
            canvas.width = image.width;
            canvas.height = image.height;
            ctx.drawImage(image, 0, 0);
            const qrCode = jsQR(ctx.getImageData(0, 0, canvas.width, canvas.height).data, canvas.width, canvas.height);
            
            if (qrCode) {
                fetch(`/validate-chemical?code=${qrCode.data}`)
                .then(response => response.json())
                .then(data => {
                    const statusBlock = document.getElementById('status-block');
                    statusBlock.classList.remove('green', 'red');
                    if (data.is_valid) {
                        statusBlock.classList.add('green');
                    } else {
                        statusBlock.classList.add('red');
                    }
                });
            } else {
                alert("No QR code detected.");
            }
        };
        image.src = imageData;
    };
    reader.readAsDataURL(input);
}
