console = {
  log: function (x) {
    call_python('log', x);
  },
};
function Node(handle) {
  this.handle = handle;
}
document = {
  querySelectorAll: function (s) {
    var handles = call_python('querySelectorAll', s);
    return handles.map(function (handle) {
      return new Node(handle);
    });
  },
};
