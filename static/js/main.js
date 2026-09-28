document.addEventListener('DOMContentLoaded', () => {
    // Client-side PDF file validation
    const fileInputs = document.querySelectorAll('input[type="file"][accept=".pdf"]');
    const MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024; // 16MB limit

    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
                alert('Invalid file format. Please select a valid PDF document (.pdf).');
                e.target.value = '';
                return;
            }

            if (file.size > MAX_FILE_SIZE_BYTES) {
                alert('File size exceeds the 16MB limit. Please upload a smaller PDF file.');
                e.target.value = '';
                return;
            }
        });
    });

    // Confirmation on forms to prevent duplicate submissions
    const forms = document.querySelectorAll('.repository-form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('.btn-submit');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Uploading...';
            }
        });
    });
});