document.addEventListener('DOMContentLoaded', function() {
  const select = document.getElementById('position-select');
  if (!select) return;
  select.addEventListener('change', function() {
    const value = this.value;
    if (!value) return;
    window.location.href = value;
  });
});