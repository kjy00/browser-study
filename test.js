var x = 2;
x + x;
console.log('Hi from JS!');

inputs = document.querySelectorAll('input');
for (var i = 0; i < inputs.length; i++) {
  let name = inputs[i].getAttribute('name');
  let value = inputs[i].getAttribute('value');
  if (value.length > 10) {
    console.log(`input ${name} is too long`);
  }
}
