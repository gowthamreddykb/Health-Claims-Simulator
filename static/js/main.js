// Health Claims Simulator - Interactive Enhancements
document.addEventListener('DOMContentLoaded', () => {
  // Password Visibility Toggle
  const showPasswordCheckbox = document.getElementById('show-password-toggle');
  const passwordInput = document.getElementById('password');
  const eyeIcon = document.getElementById('eye-icon');

  if (showPasswordCheckbox && passwordInput) {
    showPasswordCheckbox.addEventListener('change', () => {
      passwordInput.type = showPasswordCheckbox.checked ? 'text' : 'password';
      if (eyeIcon) eyeIcon.className = showPasswordCheckbox.checked ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
  }

  // Interactive Live Calculation in Officer Review Panel
  const eligibleInput = document.getElementById('eligible-amount-input');
  const calcPayoutDisplay = document.getElementById('calculated-payout-display');
  const planDeductibleEl = document.getElementById('plan-deductible-val');
  const planCopayEl = document.getElementById('plan-copay-val');

  if (eligibleInput && calcPayoutDisplay && planDeductibleEl && planCopayEl) {
    const deductible = parseFloat(planDeductibleEl.dataset.deductible || 0);
    const copay = parseFloat(planCopayEl.dataset.copay || 0);

    const updateCalc = () => {
      const eligible = parseFloat(eligibleInput.value) || 0;
      if (eligible <= 0) {
        calcPayoutDisplay.textContent = '₹0.00';
        return;
      }
      const appliedDeductible = Math.min(eligible, deductible);
      const afterDeductible = Math.max(0, eligible - appliedDeductible);
      const copayCut = afterDeductible * (copay / 100);
      const finalPayout = Math.max(0, afterDeductible - copayCut);
      calcPayoutDisplay.textContent = '₹' + finalPayout.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    };

    eligibleInput.addEventListener('input', updateCalc);
    updateCalc();
  }

  // Form decision routing for critical decisions (approve, reject, more_info)
  const reviewForm = document.getElementById('review-decision-form');
  if (reviewForm) {
    let actionField = reviewForm.querySelector('input[name="action"]');
    if (!actionField) {
      actionField = document.createElement('input');
      actionField.type = 'hidden';
      actionField.name = 'action';
      actionField.value = 'approve';
      reviewForm.appendChild(actionField);
    }
    const approveBtn = document.getElementById('btn-action-approve');
    const rejectBtn = document.getElementById('btn-action-reject');
    const moreInfoBtn = document.getElementById('btn-action-more-info');

    if (approveBtn) {
      approveBtn.addEventListener('click', () => {
        actionField.value = 'approve';
      });
    }
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => {
        actionField.value = 'reject';
      });
    }
    if (moreInfoBtn) {
      moreInfoBtn.addEventListener('click', () => {
        actionField.value = 'more_info';
      });
    }
  }

  // Dynamic Step Wizard on Claim Form if stepper buttons exist
  const step1Btn = document.getElementById('step-btn-1');
  const step2Btn = document.getElementById('step-btn-2');
  const step3Btn = document.getElementById('step-btn-3');
  const step1Pane = document.getElementById('step-pane-1');
  const step2Pane = document.getElementById('step-pane-2');
  const step3Pane = document.getElementById('step-pane-3');

  if (step1Pane && step2Pane && step3Pane) {
    const showStep = (step) => {
      [step1Pane, step2Pane, step3Pane].forEach((p, idx) => {
        if (p) p.style.display = (idx + 1 === step) ? 'block' : 'none';
      });
      [step1Btn, step2Btn, step3Btn].forEach((b, idx) => {
        if (b) {
          b.classList.toggle('active', idx + 1 === step);
          b.classList.toggle('completed', idx + 1 < step);
          b.classList.toggle('inactive', idx + 1 > step);
        }
      });
    };

    if (step1Btn) step1Btn.addEventListener('click', (e) => { e.preventDefault(); showStep(1); });
    if (step2Btn) step2Btn.addEventListener('click', (e) => { e.preventDefault(); showStep(2); });
    if (step3Btn) step3Btn.addEventListener('click', (e) => { e.preventDefault(); showStep(3); });

    const nextToStep2 = document.getElementById('btn-next-step2');
    const nextToStep3 = document.getElementById('btn-next-step3');
    const backToStep1 = document.getElementById('btn-back-step1');
    const backToStep2 = document.getElementById('btn-back-step2');

    if (nextToStep2) nextToStep2.addEventListener('click', () => showStep(2));
    if (nextToStep3) nextToStep3.addEventListener('click', () => showStep(3));
    if (backToStep1) backToStep1.addEventListener('click', () => showStep(1));
    if (backToStep2) backToStep2.addEventListener('click', () => showStep(2));
  }
});
