document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.3s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    const deleteForms = document.querySelectorAll('form[data-confirm]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm(form.dataset.confirm || 'Are you sure?')) {
            e.preventDefault();
        }
    });

    const checkboxes = document.querySelectorAll('input[type="checkbox"][data-toggle-url]');
    checkboxes.forEach(cb => {
        cb.addEventListener('change', function() {
            const url = this.dataset.toggleUrl;
            const csrf = this.dataset.csrf;
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).then(r => r.json()).then(data => {
                if (data.success !== undefined && data.total_progress !== undefined) {
                    const el = document.getElementById('total-progress');
                    if (el) el.textContent = data.total_progress + '%';
                    const fill = document.querySelector('.progress-fill-total');
                    if (fill) fill.style.width = data.total_progress + '%';
                    const ct = document.getElementById('completed-tasks');
                    if (ct && data.completed_tasks !== undefined) ct.textContent = data.completed_tasks;
                    const tt = document.getElementById('total-tasks');
                    if (tt && data.total_tasks !== undefined) tt.textContent = data.total_tasks;
                    const rt = document.getElementById('remaining-tasks');
                    if (rt && data.remaining_tasks !== undefined) rt.textContent = data.remaining_tasks;
                    if (data.course_progress !== undefined) {
                        const cp = document.getElementById('course-progress-' + data.course_id);
                        if (cp) cp.textContent = data.course_progress + '%';
                        const cpf = document.querySelector('.progress-fill-course-' + data.course_id);
                        if (cpf) cpf.style.width = data.course_progress + '%';
                    }
                }
            }).catch(err => console.error(err));
        });
    });
});

function addCourseFilterRow(containerId) {
    const container = document.getElementById(containerId);
    const row = document.createElement('div');
    row.className = 'course-filter-row';
    row.innerHTML = `
        <input type="text" name="course_code[]" class="input" placeholder="Course Code (e.g. CSE3201)">
        <input type="text" name="section[]" class="input" placeholder="Section">
        <select name="strength[]" class="select">
            <option value="1">Very Easy</option>
            <option value="2">Easy</option>
            <option value="3" selected>Medium</option>
            <option value="4">Hard</option>
            <option value="5">Very Hard</option>
        </select>
        <button type="button" class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(row);
}

function checkQuiz(mcqIndex, correctIndex) {
    const options = document.querySelectorAll(`#mcq-${mcqIndex} .quiz-option`);
    options.forEach((opt, i) => {
        opt.classList.remove('correct', 'incorrect');
        if (i === correctIndex) {
            opt.classList.add('correct');
        } else if (opt.querySelector('input').checked) {
            opt.classList.add('incorrect');
        }
    });
}
