const expressionEl = document.getElementById('expression');
const resultEl = document.getElementById('result');

let currentValue = '0';
let previousValue = '';
let operator = null;
let shouldResetDisplay = false;

const OPERATOR_SYMBOLS = {
  '+': '+',
  '-': '−',
  '*': '×',
  '/': '÷',
};

function updateDisplay() {
  resultEl.textContent = formatDisplay(currentValue);

  if (previousValue && operator) {
    expressionEl.textContent = `${formatDisplay(previousValue)} ${OPERATOR_SYMBOLS[operator]}`;
  } else {
    expressionEl.textContent = '';
  }
}

function formatDisplay(value) {
  if (value === '' || value === '-') return value || '0';

  const num = parseFloat(value);
  if (isNaN(num)) return '0';

  if (value.includes('.') && value.endsWith('.')) {
    const intPart = parseInt(value, 10);
    return intPart.toLocaleString('id-ID') + '.';
  }

  const parts = value.split('.');
  const intPart = parseInt(parts[0], 10);
  const formatted = intPart.toLocaleString('id-ID');

  return parts.length > 1 ? `${formatted},${parts[1]}` : formatted;
}

function inputNumber(digit) {
  if (shouldResetDisplay) {
    currentValue = digit === '.' ? '0.' : digit;
    shouldResetDisplay = false;
  } else if (digit === '.' && currentValue.includes('.')) {
    return;
  } else if (currentValue === '0' && digit !== '.') {
    currentValue = digit;
  } else {
    currentValue += digit;
  }
  updateDisplay();
}

function inputOperator(op) {
  if (operator && !shouldResetDisplay) {
    calculate();
  }

  previousValue = currentValue;
  operator = op;
  shouldResetDisplay = true;
  updateDisplay();
}

function calculate() {
  if (!operator || previousValue === '') return;

  const prev = parseFloat(previousValue);
  const current = parseFloat(currentValue);

  if (isNaN(prev) || isNaN(current)) return;

  let result;

  switch (operator) {
    case '+':
      result = prev + current;
      break;
    case '-':
      result = prev - current;
      break;
    case '*':
      result = prev * current;
      break;
    case '/':
      if (current === 0) {
        currentValue = 'Error';
        previousValue = '';
        operator = null;
        shouldResetDisplay = true;
        expressionEl.textContent = '';
        resultEl.textContent = 'Error';
        return;
      }
      result = prev / current;
      break;
    default:
      return;
  }

  const resultStr = roundResult(result);
  expressionEl.textContent = `${formatDisplay(previousValue)} ${OPERATOR_SYMBOLS[operator]} ${formatDisplay(currentValue)} =`;
  currentValue = resultStr;
  previousValue = '';
  operator = null;
  shouldResetDisplay = true;
  resultEl.textContent = formatDisplay(currentValue);
}

function roundResult(num) {
  const rounded = Math.round(num * 1e10) / 1e10;
  return String(rounded);
}

function clearAll() {
  currentValue = '0';
  previousValue = '';
  operator = null;
  shouldResetDisplay = false;
  updateDisplay();
}

function toggleSign() {
  if (currentValue === '0' || currentValue === 'Error') return;
  currentValue = currentValue.startsWith('-')
    ? currentValue.slice(1)
    : '-' + currentValue;
  updateDisplay();
}

function percentage() {
  const num = parseFloat(currentValue);
  if (isNaN(num)) return;
  currentValue = roundResult(num / 100);
  shouldResetDisplay = true;
  updateDisplay();
}

document.querySelector('.keypad').addEventListener('click', (e) => {
  const btn = e.target.closest('.btn');
  if (!btn) return;

  const action = btn.dataset.action;
  const value = btn.dataset.value;

  if (value !== undefined) {
    inputNumber(value);
    return;
  }

  switch (action) {
    case 'clear':
      clearAll();
      break;
    case 'toggle-sign':
      toggleSign();
      break;
    case 'percent':
      percentage();
      break;
    case 'operator':
      inputOperator(value);
      break;
    case 'equals':
      calculate();
      break;
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key >= '0' && e.key <= '9') {
    inputNumber(e.key);
  } else if (e.key === '.') {
    inputNumber('.');
  } else if (e.key === '+' || e.key === '-' || e.key === '*' || e.key === '/') {
    e.preventDefault();
    inputOperator(e.key);
  } else if (e.key === 'Enter' || e.key === '=') {
    e.preventDefault();
    calculate();
  } else if (e.key === 'Escape') {
    clearAll();
  } else if (e.key === '%') {
    percentage();
  }
});

updateDisplay();
