document.addEventListener('DOMContentLoaded', () => {
    const incomeBtn = document.getElementById('showIncome');
    const expenseBtn = document.getElementById('showExpense');
    const incomeForm = document.getElementById('incomeForm');
    const expenseForm = document.getElementById('expenseForm');

    incomeBtn.addEventListener('click', () => {
        incomeForm.classList.add('active');
        expenseForm.classList.remove('active');
    });

    expenseBtn.addEventListener('click', () => {
        expenseForm.classList.add('active');
        incomeForm.classList.remove('active');
    });
});
