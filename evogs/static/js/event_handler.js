document.addEventListener('DOMContentLoaded', domReady);

function domReady() {
  // Initialize every dics slider present on the page. Iterating instead of
  // hard-coding [0]/[1] avoids errors when a section is added or removed.
  document.querySelectorAll('.b-dics').forEach(function (el) {
    new Dics({
      container: el,
      hideTexts: false,
      textPosition: "bottom"
    });
  });
}

// Swap the 5-method qualitative slider to the requested LOD (0..3) and
// update the active tab styling. Method order MUST match the <img> order
// in the .b-dics container in index.html.
function evogsQualEvent(idx) {
  var dics = document.querySelectorAll('.b-dics')[0];
  if (!dics) return;
  var sections = dics.getElementsByClassName('b-dics__section');
  var methods = ['mono', 'single', 'lapis', 'sym', 'asym'];
  for (var i = 0; i < methods.length; i++) {
    var image = sections[i]
      .getElementsByClassName('b-dics__image-container')[0]
      .getElementsByClassName('b-dics__image')[0];
    image.src = 'static/images/visualization/' + methods[i] + '_l' + idx + '.png';
  }

  var tabs = document.getElementById('evogs-qual-tabs').children;
  for (var i = 0; i < tabs.length; i++) {
    tabs[i].children[0].className = (idx === i) ? 'nav-link active' : 'nav-link';
  }
}
