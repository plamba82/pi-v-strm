// CHANGE: Log click coordinates to console
document.addEventListener('click', function(event) {
    console.log(`You clicked at x, y = ${event.clientX}, ${event.clientY}`);
});