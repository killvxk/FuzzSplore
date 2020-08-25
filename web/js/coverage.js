// set the dimensions and margins of the graph
var margin = {top: 10, right: 30, bottom: 30, left: 60},
    width = 460 - margin.left - margin.right,
    height = 400 - margin.top - margin.bottom;

// append the svg object to the body of the page
var svg = d3.select("#coverage")
  .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform",
          "translate(" + margin.left + "," + margin.top + ")");

d3.csv("http://0.0.0.0:8888/data/coverage.csv", function(data) {

  var ptsize = 1.5

  var xmin = d3.min(data, (d) => { return +d.TIMEs; }) -ptsize
  var xmax = d3.max(data, (d) => { return +d.TIME; }) +ptsize
  
  var ymin = d3.min(data, (d) => { return +d.VAL; }) -ptsize
  var ymax = d3.max(data, (d) => { return +d.VAL; }) +ptsize
  
  const colorScale = d3.scaleOrdinal()
        .range(d3.schemeCategory10);

    // Add X axis
    var x = d3.scaleLinear()
      .domain([xmin, xmax])
      .range([ 0, width ]);
    svg.append("g")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x));

    // Add Y axis
    var y = d3.scaleLinear()
      .domain([ymin, ymax])
      .range([ height, 0 ]);
    svg.append("g")
      .call(d3.axisLeft(y));

    // Add the line
    svg.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", function (d) { return colorScale(d.NAME); })
      .attr("stroke-width", 1.5)
      .attr("d", d3.line()
        .x(function(d) { return x(d.TIME) })
        .y(function(d) { return y(d.VAL) })
        )

})
