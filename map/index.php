<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="initial-scale=1.0, user-scalable=no" />
<style type="text/css">
  html { height: 100% }
  body { height: 100%; margin: 0px; padding: 0px }
  #map_canvas { height: 100% }
</style>
<script type="text/javascript"
    src="http://maps.google.com/maps/api/js?sensor=false">
</script>
<script type="text/javascript">
function CoordMapType() {
}

CoordMapType.prototype.tileSize = new google.maps.Size(256,256);
CoordMapType.prototype.maxZoom = 19;

CoordMapType.prototype.getTile = function(coord, zoom, ownerDocument) {
  var div = ownerDocument.createElement('DIV');

  zoom += 1; //err bug in script i was using

  if(zoom == 15 || zoom == 14) {
    div.innerHTML = "<img src=\"tiles/"+zoom+"/z"+zoom+"x"+coord.x+"y"+coord.y+".png\"/>";
  } else {
    div.innerHTML = coord + " " + zoom;
    div.style.width = this.tileSize.width + 'px';
    div.style.height = this.tileSize.height + 'px';
    div.style.fontSize = '10';
    div.style.borderStyle = 'solid';
    div.style.borderWidth = '1px';
    div.style.borderColor = '#AAAAAA';
  }
  return div;
};

CoordMapType.prototype.name = "Tile #s";
CoordMapType.prototype.alt = "Tile Coordinate Map Type";

var map;
//var chicago = new google.maps.LatLng(41.850033,-87.6500523);
var chicago = new google.maps.LatLng(53.852,-3.038);
var coordinateMapType = new CoordMapType();

function initialize() {
  var mapOptions = {
    zoom: 10,
    center: chicago,
    mapTypeControlOptions: {
      mapTypeIds: ['coordinate', google.maps.MapTypeId.ROADMAP],
      style: google.maps.MapTypeControlStyle.DROPDOWN_MENU
    }
  };
  map = new google.maps.Map(document.getElementById("map_canvas"),
      mapOptions);
      
  // Now attach the coordinate map type to the map's registry
  map.mapTypes.set('coordinate',coordinateMapType);

  // We can now set the map to use the 'coordinate' map type
  map.setMapTypeId('coordinate');
}
</script>
</head>
<body onload="initialize()">
  <div id="map_canvas" style="width:100%; height:100%"></div>
</body>
</html>

