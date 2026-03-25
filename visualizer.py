import colorsys
import json
import folium
import math
from datetime import datetime
from dateutil.parser import parse

class Point():
    def __init__(self, coordinate, source, timestamp, accuracy):
        self.coordinate = coordinate
        self.source = source
        self.timestamp = timestamp
        self.accuracy = accuracy

    def to_dict(self):
        return {
            'coordinate': self.coordinate,
            'source': self.source,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'accuracy': self.accuracy
        }
    
    @staticmethod
    def extract_coordinates_from_point(data_list):
        return [item['coordinate'] for item in data_list]

def total_coords(coordinateSets):
    total = 0

    for coordSet in coordinateSets:
        total += len(coordSet)

    return total

def coords_from_point(coordSet):
    return Point.extract_coordinates_from_point(coordSet)

def coords_to_dictionary(coordinates):
    for coordSet in coordinates["coordinateSets"]:
        for c in range(len(coordSet)):
            coordSet[c] = coordSet[c].to_dict()

    return coordinates

def dist_between_coords(c1, c2):
    return math.dist(c1, c2)

def time_distance(t1, t2):
    time_diff = datetime.fromisoformat(t1.replace("Z", "+00:00")) - datetime.fromisoformat(t2.replace("Z", "+00:00"))
    hour_diff = time_diff.total_seconds() / 60 / 60
    return hour_diff
    
def get_date_color(coordSet):
    timestamp = coordSet[0]['timestamp']

    # Parse the input date string
    parsed_date = parse(timestamp)
    parsed_date = parsed_date.replace(tzinfo=None)
    
    # Define the start and end dates
    start_date = datetime(2014, 1, 1)
    end_date = datetime.now()
    
    # Calculate the total time range and the position of the input date
    total_range = (end_date - start_date).total_seconds()
    date_position = (parsed_date - start_date).total_seconds()
    
    # Normalize the position to a value between 0 and 1
    normalized_position = date_position / total_range
    
    # Convert the normalized position to a color (red to blue)
    hue = normalized_position * 0.66  # 0.66 is the hue for blue in HSV
    rgb = colorsys.hsv_to_rgb(hue, 1, 1)
    
    # Convert RGB values to hexadecimal color code
    hex_color = "#{:02x}{:02x}{:02x}".format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
    
    return hex_color

def get_accuracy_opacity(coordSet):

    total_acc = 0
    for coord in coordSet:
        total_acc += coord['accuracy']

    accuracy = total_acc / len(coordSet)

    if (accuracy >= 20):
        return 0.4
    elif (accuracy >= 15 and accuracy < 20):
        return 0.5
    elif (accuracy >= 10 and accuracy < 15):
        return 0.6
    elif (accuracy >= 5 and accuracy < 10):
        return 0.7
    elif (accuracy >= 0 and accuracy < 5):
        return 0.8

# Extracts the coordinates from the Records.json and puts the valid ones into a big list
def extract_coordinates(json_data):

    # Get number of raw coordinates in file
    num_of_coords = len(json_data["locations"])
    print("Found " + str(num_of_coords) + " coordinates, extracting...")

    # initialize output coordinateSet json file
    coordinate_sets = {"coordinateSets" : []}
    coordinate_sets["coordinateSets"].append([])

    # initialize last coordinate as first in file
    last_coord = (json_data["locations"][0]["latitudeE7"]/ 10000000.0, json_data["locations"][0]["longitudeE7"]/ 10000000.0)
    last_time = json_data["locations"][0]["timestamp"]
    last_source = json_data["locations"][0]["source"]
    this_coord = ()
    this_time = ""

    # a checker if a coordinate is way off, close the current set and start a new one
    set_to_add_to = 0

    for item in json_data["locations"]:
    
        # get latitude and longitude from raw file & set them to a coordinate pair
        try:
            lat = item["latitudeE7"] / 10000000.0
            lon = item["longitudeE7"] / 10000000.0
            this_coord = (lat, lon)
            this_time = item["timestamp"]
            accuracy = item["accuracy"]
            source = item["source"]

            time_diff = time_distance(this_time, last_time)
            dist_diff = dist_between_coords(last_coord, this_coord)

            # remove inaccurate coordinates
            if (accuracy > 35 or source == "CELL"):
                continue
            
            # check if this coordinate and the last one are close enough
            # if they are, then add those coordinates to the current set
            # else, we need a new set, don't add these coordinates
            if dist_diff < 0.12 and time_diff < 0.03 and (source != "WIFI" or last_source != "WIFI" or dist_diff < 0.002):
                new_point = Point(this_coord, source, this_time, accuracy)
                coordinate_sets["coordinateSets"][set_to_add_to].append(new_point)
            else:
                coordinate_sets["coordinateSets"].append([])
                set_to_add_to += 1
                new_point = Point(this_coord, source, this_time, accuracy)
                coordinate_sets["coordinateSets"][set_to_add_to].append(new_point)

            last_coord = this_coord
            last_time = this_time
        except:
            continue

    print("Extracted "+ str(total_coords(coordinate_sets["coordinateSets"])) + " coordinates. Cleaning...")

    # remove any sets with only 2 coordinate pairs in it
    cleaned_coordinate_sets = {"coordinateSets" : []}
    for coordinate_set in coordinate_sets["coordinateSets"]:
        if (len(coordinate_set) > 2):
            cleaned_coordinate_sets["coordinateSets"].append(coordinate_set)

    print("Cleaned coordinates. " + str(total_coords(cleaned_coordinate_sets["coordinateSets"])) + " coordinates remaining.")

    return cleaned_coordinate_sets

# Open the JSON file
print("Opening Records.json, this can take a while...")
with open('Records.json', 'r') as file:
    data = json.load(file)

# Call the function to extract coordinates
coordinates = extract_coordinates(data)

# Save dictionary to a JSON file
with open("extractedCoords.json", "w") as outfile:
    json.dump(coords_to_dictionary(coordinates), outfile, indent=4, sort_keys=True)

print("Coordinates extracted and saved to file, creating map...")

# Create a map object
map = folium.Map(location=[53, -1], zoom_start=7, tiles="Cartodb dark_matter")

# Create PolyLine objects to connect the coordinates
print("Sets to add: " + str(len(coordinates["coordinateSets"])))
for coordSet in coordinates["coordinateSets"]:
    lines = folium.PolyLine(locations=coords_from_point(coordSet), color=get_date_color(coordSet), weight=1.5, opacity=get_accuracy_opacity(coordSet), smooth_factor=0, popup=f"{str(coordSet)}")
    # Add the PolyLines to the map
    lines.add_to(map)

# Display the map
map.save('map.html')

print("Map created!")