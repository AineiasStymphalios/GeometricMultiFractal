from CvPythonExtensions import *
import CvUtil
import CvMapGeneratorUtil
from CvMapGeneratorUtil import MultilayeredFractal
from CvMapGeneratorUtil import TerrainGenerator
from CvMapGeneratorUtil import FeatureGenerator
import math

'''
##############################################################################
MULTILAYERED FRACTAL NOTES

The MultilayeredFractal class was created for use with this script.

I worked to make it adaptable to other scripts, though, and eventually it
migrated in to the MapUtil file along with the other primary map classes.

- Bob Thomas July 13, 2005


TERRA NOTES

Terra turns out to be our largest size map. This is the only map script
in the original release of Civ4 where the grids are this large!

This script is also the one that got me started in to map scripting. I had 
this idea early in the development cycle and just kept pestering until Soren 
turned me loose on it, finally. Once I got going, I just kept on going!

- Bob Thomas   September 20, 2005

EARTH2 NOTES

This is based purely on the Terra script, albeit with a lot more similarity
to Earth in terms of landmasses. Rocky Climate and Normal Sea Levels strongly
recommended for maximum earthiness.

##############################################################################
MEDITERRANEAN, CENTRAL PLAINS, GEOMETRIC MULTIFRACTAL NOTES

This mapscript was based on Earth2.py.

Below are its features:
- GeometricMultiFractal Genrator: an improved MultilayeredFractal generator
	- Takes matrix inputs
	- More property inputs for regions
	- Allows Rectangular, Elliptical, and Triangular fractal masks with rotation.
- Custom Climate Generator
	- Generates terrain and features based on custom-placed temperature and moisture vectors.
- Bonus generator
	- Rewrote Vanilla's strategic and food bonus additions to starting plots
	- Option: Historical resource placement
		- Swaps / removes ahistoric resources
		- Region specific bonus placement
- Custom River / Waterway Generator
	- Allows generation of rivers and waterways through map coordinates.
- Default River generator replaced with generator based on that of Tectonics.py
- Two tile coasts (expandCoastToTwoTiles)
- Option: Historical starting locations
	- Historical (Shuffle): Randomly places all players in primary, secondary, and tertiary locations, in order of priority. 
		Remaining players are placed with default methods.
	- Historical (Fixed): If there are any map-appropriate Vanilla BTS Civilizations in the playerlist, they are placed on fixed regions. 
		Remaining players assignments fall back to the Shuffle method, and then to default methods.
- Option: Mountain range settings

- AineiasStymph, April 29, 2026
##############################################################################
'''


	
def getDescription():
	desc = "A procedurally generated Chinese Central Plains map, inspired by the Chinese Unification mod-scenario in Warlords."
	desc += "Features options for geography and climate."
	return desc

def isAdvancedMap():
	"This map should show up in simple mode"
	return 0


# -----------------------------------------------------------------------------
# Custom Options
# -----------------------------------------------------------------------------
def getNumCustomMapOptions():
	return 6

def getCustomMapOptionName(argsList):
	index = argsList[0]
	names = [
		"Geographic Accuracy",
		"Peak Reduction",
		"River Options",
		"Historical Resources",
		"Minimum land food at start",
		"Start Options"
	]
	if index < len(names):
		return names[index]
	return ""

def getNumCustomMapOptionValues(argsList):
	index = argsList[0]
	if index == 0: return 3 # Geographic Accuracy
	if index == 1: return 3 # Peaks: Flatten Alpine, Highland, Disabled
	if index == 2: return 4 # Rivers: Disabled, Regular, Bridged Waterway, Bridgeless
	if index == 3: return 2 # Historical Resources: Yes/No
	if index == 4: return 3 # Food: 0, 1, 2
	if index == 5: return 2 # Start Options: Default, Fixed-Shuffle
	return 0

def getCustomMapOptionDescAt(argsList):
	index = argsList[0]
	selection = argsList[1]
	if index == 0: # Accuracy
		if selection == 0: return "High (Australia)"
		if selection == 1: return "Medium (Simplified China)"
		return "Low (Shapes)"
	if index == 1: # Peaks
		if selection == 0: return "Flatten Alpine Regions"
		if selection == 1: return "Flatten Alpine and Highland Regions"
		return "Disabled (Allow all)"
	if index == 2: # Rivers
		if selection == 0: return "Disabled"
		if selection == 1: return "Regular Rivers"
		if selection == 2: return "Bridged Waterways"
		return "Bridgeless Waterways"
	if index == 3: # Historical Resources
		if selection == 0: return "Historical Placement"
		return "Vanilla Distribution"
	if index == 4: # Food
		if selection == 0: return "Standard"
		if selection == 1: return "At least 1"
		return "At least 2"
	if index == 5: # Start Options
		if selection == 0: return "Vanilla"
		return "Historical"
	return ""

def getCustomMapOptionDefault(argsList):
	index = argsList[0]
	if index == 0: return 0 # High
	if index == 1: return 2 # Disabled
	if index == 2: return 1 # Regular Rivers
	if index == 3: return 0 # Historical
	if index == 4: return 1 # 1 Food
	if index == 5: return 0 # Vanilla
	return 0

# -----------------------------------------------------------------------------
# Map Properties
# -----------------------------------------------------------------------------

def getGridSize(argsList):
	# Sse map sizes here. Multiply each dimension by 4x to get map width and height.
	grid_sizes = {
		WorldSizeTypes.WORLDSIZE_DUEL:      (8, 6),
		WorldSizeTypes.WORLDSIZE_TINY:      (9, 6),
		WorldSizeTypes.WORLDSIZE_SMALL:     (10, 7),
		WorldSizeTypes.WORLDSIZE_STANDARD:  (12, 8),
		WorldSizeTypes.WORLDSIZE_LARGE:     (13, 9),
		WorldSizeTypes.WORLDSIZE_HUGE:      (15, 10),
	}
	if argsList[0] == -1:
		return []
	return grid_sizes[argsList[0]]

def isSeaLevelMap():
	return 0

def getWrapX():
	return False

def getWrapY():
	return False

def isClimateMap():
	return 1

def getClimate():
	"""This is now ignored by the engine because isClimateMap is 1, 
	but we keep it for safety."""
	return ClimateTypes.CLIMATE_TEMPERATE

_all_start_coords = [] # Store player start coords
def beforeGeneration():
	"""
	Official Civ4 hook called before map generation starts.
	Guaranteed to run on Map Regeneration and New Games.
	"""
	# Clear the starting plot cache
	global _START_PLOT_MAP
	_START_PLOT_MAP = None
	
	# RESET CLIMATE GLOBALS HERE to prevent settings from "sticking"
	global _CLIMATE_ENGINE
	_CLIMATE_ENGINE = None
	
	return None

_DEBUG_REGIONS = [] # Global to store regions for sign placement

def _add_region_signs(region_data):
	"""Adds map signs to the center of each fractal region."""
	m = CyMap()
	engine = CyEngine()
	iW = m.getGridWidth()
	iH = m.getGridHeight()
	
	for data in region_data:
		name = data[0]
		cx = data[2]
		cy = data[3]
		
		# Convert fractional center to plot coordinates
		iX = int(iW * cx)
		iY = int(iH * cy)
		
		pPlot = m.plot(iX, iY)
		if pPlot and not pPlot.isNone():
			# -1 makes the sign visible to all players (global)
			engine.addSign(pPlot, -1, str(name))



# -----------------------------------------------------------------------------
# GeometricMultiFractal Generator
# -----------------------------------------------------------------------------
class GeometricMultiFractal(CvMapGeneratorUtil.MultilayeredFractal):
	"""
	Fractal generator supporting geometric masking and rotation.
	Shapes: RECT, ELLIPSE, ISOTRI.
	"""
	def generatePlotsByRegion(self, region_data):
		sea = 0 
		
		# Define Terrain Profiles: (HillDensity%, PeakDensity%_of_Hills)
		terrain_profiles = {
			"flat":         (15, 1),
			"plateau":      (60, 25),
			"highland":     (75, 40),
			"alpine":       (95, 60),
			"default":      (30, 20)
		}
		
		gc = CyGlobalContext()
		m = CyMap()
		iRocky = gc.getInfoTypeForString("CLIMATE_ROCKY")
		if m.getClimate() == iRocky:
			for key in terrain_profiles.keys():
				h_dens, p_dens = terrain_profiles[key]
				new_h = int(h_dens * 1.2)
				new_p = int(p_dens * 1.1)
				if new_h > 100: new_h = 100
				if new_p > 100: new_p = 100
				terrain_profiles[key] = (new_h, new_p)

		for data in region_data:
			name, r_type_raw, cx, cy, d1, d2, d3, terrain, grain, h_grain, water_prc = data
			r_type = r_type_raw.upper()
			
			# 1. Coordinate Math
			center_x = cx * self.iW
			center_y = cy * self.iH
			radius_x = (d1 / 2.0) * self.iW
			radius_y = (d2 / 2.0) * self.iH
			height_tiles = d2 * self.iH
			max_radius_tiles = math.sqrt(radius_x**2 + radius_y**2)
			
			iWest = max(0, int(center_x - max_radius_tiles))
			iEast = min(self.iW - 1, int(center_x + max_radius_tiles))
			iSouth = max(0, int(center_y - max_radius_tiles))
			iNorth = min(self.iH - 1, int(center_y + max_radius_tiles))
			
			reg_w, reg_h = iEast - iWest + 1, iNorth - iSouth + 1
			if reg_w <= 0 or reg_h <= 0: continue

			# 2. Fractal Initialization
			NiTextOut("Generating %s (Geometric Fractal) ..." % name)
			
			# This fractal is now shared by BOTH Land and Water regions
			regionContFrac = CyFractal()
			regionContFrac.fracInit(reg_w, reg_h, grain, self.dice, 0, -1, -1)
			
			# Calculate threshold for the "Active" part of the fractal
			if water_prc <= 0:
				iWaterThreshold = -1
			elif water_prc >= 100:
				iWaterThreshold = 255
			else:
				iWaterThreshold = regionContFrac.getHeightFromPercent(water_prc + sea)

			is_subtractive = (terrain == "water")
			
			# Only Land regions need Hill/Peak fractals
			if not is_subtractive:
				regionHillsFrac = CyFractal()
				regionPeaksFrac = CyFractal()
				regionHillsFrac.fracInit(reg_w, reg_h, h_grain, self.dice, 0, -1, -1)
				regionPeaksFrac.fracInit(reg_w, reg_h, h_grain+1, self.dice, 0, -1, -1)

				h_dens, p_dens = terrain_profiles.get(terrain, terrain_profiles["default"])
				iHillThreshold = regionHillsFrac.getHeightFromPercent(100 - h_dens)
				iPeakThreshold = regionPeaksFrac.getHeightFromPercent(100 - p_dens)

			# Rotation/Geometry Math
			rad = -math.radians(d3)
			cosA, sinA = math.cos(rad), math.sin(rad)
			v_dist, b_dist = (2.0 / 3.0) * height_tiles, (1.0 / 3.0) * height_tiles
			invRxSq, invRySq = 0.0, 0.0
			if radius_x > 0: invRxSq = 1.0 / (radius_x * radius_x)
			if radius_y > 0: invRySq = 1.0 / (radius_y * radius_y)

			# 3. Iterate over the grid
			for x in range(reg_w):
				world_x = x + iWest
				# Add 0.5 to world_x to get the center of the tile
				dx = (float(world_x) + 0.5) - center_x
				for y in range(reg_h):
					world_y = y + iSouth
					# Add 0.5 to world_y to get the center of the tile
					dy = (float(world_y) + 0.5) - center_y

					# Now, tiles on either side of an even-numbered split will have 
					# identical distance values (e.g., -0.5 and 0.5).
					# Geometry Check
					rx = dx * cosA - dy * sinA
					ry = dx * sinA + dy * cosA
					is_inside = False
					if r_type == "ELLIPSE":
						if (rx*rx * invRxSq) + (ry*ry * invRySq) <= 1.0: is_inside = True
					elif r_type == "ISOTRI":
						if ry >= -b_dist and ry <= v_dist:
							max_rx = radius_x * (v_dist - ry) / height_tiles
							if abs(rx) <= max_rx: is_inside = True
					else: # RECT
						if abs(rx) <= radius_x and abs(ry) <= radius_y: is_inside = True

					if not is_inside: continue
						
					# Decide plot type
					world_i = world_y * self.iW + world_x
					val = regionContFrac.getHeight(x, y)
					
					if is_subtractive:
						# WATER REGION: If fractal roll is within the water percent, punch a hole.
						# Setting water_prc=100 will now correctly turn every tile to ocean.
						if val <= iWaterThreshold:
							self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_OCEAN
					else:
						# LAND REGION: Skip tiles within the water percent threshold (remains ocean).
						if val <= iWaterThreshold: 
							continue
						
						# Process Hills and Peaks for land
						if regionHillsFrac.getHeight(x, y) >= iHillThreshold:
							if regionPeaksFrac.getHeight(x, y) >= iPeakThreshold:
								self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_PEAK
							else:
								self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_HILLS
						else:
							self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_LAND
							
		return self.wholeworldPlotTypes

def generatePlotTypes():
	"""Specify map regions here."""
	NiTextOut("Setting Plot Types (Python Central Plains) ...")
	
	global _START_PLOT_MAP, _DEBUG_REGIONS
	_START_PLOT_MAP = None

	gc = CyGlobalContext()
	m = CyMap()
	climate = m.getClimate()
	
	accuracy = m.getCustomMapOption(0)
	peak_opt = m.getCustomMapOption(1)
	
	sizekey = m.getWorldSize()
	sizevalues = {
		WorldSizeTypes.WORLDSIZE_DUEL:      (3,2,1),
		WorldSizeTypes.WORLDSIZE_TINY:      (3,2,1),
		WorldSizeTypes.WORLDSIZE_SMALL:     (4,2,1),
		WorldSizeTypes.WORLDSIZE_STANDARD:  (4,2,1),
		WorldSizeTypes.WORLDSIZE_LARGE:     (4,2,1),
		WorldSizeTypes.WORLDSIZE_HUGE:      (5,2,1)
	}
	(ScatterGrain, BalanceGrain, GatherGrain) = sizevalues[sizekey]
	ZeroGrain = 0
	
	regions = []
	if accuracy == 0: # High ACCURACY
		# Name, Type, CX, CY, W, H, Angle, Terrain, Grain, Hills, Water%
		regions = [
			("Darwin", "Ellipse", 0.439, 0.846, 0.161, 0.099, 0, "default", BalanceGrain, BalanceGrain, 5),
			("QL_NSW_VIC", "Ellipse", 0.616, 0.433, 0.356, 0.412, 266, "default", GatherGrain, BalanceGrain, 5),
			("NorthernT", "Ellipse", 0.495, 0.672, 0.332, 0.197, -28, "plateau", BalanceGrain, BalanceGrain, 5),
			("GreatSandyDesert", "Rect", 0.313, 0.644, 0.206, 0.257, 50, "default", BalanceGrain, BalanceGrain, 10),
			("WestAustralia", "Rect", 0.222, 0.454, 0.208, 0.389, 24, "default", BalanceGrain, BalanceGrain, 5),
			("Cape York", "Isotri", 0.615, 0.744, 0.123, 0.280, 1, "default", BalanceGrain, BalanceGrain, 10),
			("GDR_South", "Ellipse", 0.667, 0.339, 0.239, 0.122, 61, "highland", BalanceGrain, BalanceGrain, 0),
			("GDR_N", "Ellipse", 0.665, 0.570, 0.280, 0.115, -63, "highland", BalanceGrain, BalanceGrain, 0),
			("SouthAustralia", "Rect", 0.439, 0.390, 0.230, 0.339, -1, "flat", BalanceGrain, ScatterGrain, 0),
			("Ellipse7", "Ellipse", 0.419, 0.587, 0.188, 0.188, 0, "highland", ScatterGrain, ScatterGrain, 10),
			("SA_Plateau", "Ellipse", 0.530, 0.338, 0.080, 0.161, -31, "plateau", ScatterGrain, BalanceGrain, 0),
			("Ellipse8", "Ellipse", 0.313, 0.729, 0.072, 0.122, 24, "plateau", BalanceGrain, BalanceGrain, 0),
			("Tasmania", "Isotri", 0.629, 0.082, 0.114, 0.125, 180, "plateau", GatherGrain, BalanceGrain, 5),
			("SouthNZ", "Rect", 0.875, 0.136, 0.083, 0.225, 319, "default", BalanceGrain, BalanceGrain, 12),
			("NorthNZ", "Rect", 0.944, 0.275, 0.075, 0.135, -29, "default", BalanceGrain, BalanceGrain, 30),
			("Northland", "Ellipse", 0.906, 0.377, 0.091, 0.040, -55, "flat", BalanceGrain, BalanceGrain, 10),
			("EastIndies", "Rect", 0.127, 0.953, 0.256, 0.095, 0, "default", ScatterGrain, BalanceGrain, 60),
			("NG_PortMoresby", "Ellipse", 0.706, 0.934, 0.146, 0.074, -49, "plateau", BalanceGrain, BalanceGrain, 20),
			("NewGuinea", "Ellipse", 0.607, 0.998, 0.183, 0.089, 0, "default", BalanceGrain, BalanceGrain, 20),
			("Timor", "Rect", 0.318, 0.955, 0.131, 0.048, 29, "default", GatherGrain, BalanceGrain, 20),
			("Coral_Sea", "Rect", 0.753, 0.734, 0.091, 0.094, -24, "alpine", ScatterGrain, BalanceGrain, 85),
			("GreatAustBight", "Ellipse", 0.356, 0.208, 0.314, 0.309, 0, "water", BalanceGrain, BalanceGrain, 90),
			("WA Plateau", "Rect", 0.206, 0.500, 0.126, 0.200, 22, "plateau", BalanceGrain, BalanceGrain, 0),
			("Rottnest_Is", "Rect", 0.107, 0.280, 0.060, 0.077, 0, "default", ScatterGrain, ScatterGrain, 85),
			("New_Caledonia", "Rect", 0.925, 0.641, 0.062, 0.042, 324, "default", ScatterGrain, BalanceGrain, 50),
			("LordHowe_Norfolk_Isl", "Rect", 0.822, 0.410, 0.056, 0.283, 0, "default", ScatterGrain, BalanceGrain, 90),
		]
	elif accuracy == 1: # Medium ACCURACY
		# Name, Type, CX, CY, W, H, Angle, Terrain, Grain, Hills, Water%
		regions = [
			("Low_Fractal_Mainland", "Rect", 0.25, 0.50, 0.70, 1.2, 0, "default", ScatterGrain, ScatterGrain, 0),
			("Low_Fractal_WesternMountains", "Rect", 0.05, 0.50, 0.2, 1.2, 0, "highland", ScatterGrain, ScatterGrain, 10),
			("Low_Fractal_Coast", "Ellipse", 0.4, 0.2, 0.9, 0.9, 0, "default", BalanceGrain, ScatterGrain, 15),
			("Low_Fractal_North", "Ellipse", 0.8, 0.96, 0.6, 0.4, 45, "default", BalanceGrain, ScatterGrain, 20)
		]
	else: # LOW Accuracy = Shapes
		# Name, Type, CX, CY, W, H, Angle, Terrain, Grain, Hills, Water%
		regions = [
			("FlatRect", "Rect", 0.25, 0.75, 0.15, 0.15, 45, "flat", GatherGrain, BalanceGrain, 0),
			("DefaultEllipse", "Ellipse", 0.50, 0.75, 0.2, 0.3, 30, "default", GatherGrain, BalanceGrain, 0),
			("PlateauIso", "Isotri", 0.75, 0.75, 0.2, 0.2, 0, "plateau", GatherGrain, BalanceGrain, 0),
			
			("HighlandRect", "Rect", 0.25, 0.5, 0.15, 0.15, 0, "highland", GatherGrain, BalanceGrain, 0),
			("AlpineRect", "Rect", 0.50, 0.5, 0.15, 0.15, 0, "alpine", GatherGrain, BalanceGrain, 0),
			("WaterRect", "Rect", 0.75, 0.5, 0.2, 0.2, 80, "flat", GatherGrain, BalanceGrain, 0),
			("WaterEllipse", "Ellipse", 0.75, 0.5, 0.10, 0.10, 45, "water", BalanceGrain, BalanceGrain, 100),
			
			("GatherGrainRect", "Rect", 0.25, 0.25, 0.15, 0.15, 0, "default", GatherGrain, BalanceGrain, 30),
			("BalanceGrainRect", "Rect", 0.50, 0.25, 0.15, 0.15, 0, "default", BalanceGrain, BalanceGrain, 30),
			("ScatterGrainRect", "Rect", 0.75, 0.25, 0.15, 0.15, 0, "default", ScatterGrain, BalanceGrain, 30),
		]


	# Peak Reduction Logic
	processed_regions = []
	for r in regions:
		r_list = list(r)
		terrain = r_list[7]
		if peak_opt == 0: # Flatten Alpine
			if terrain == "alpine": r_list[7] = "highland"
		elif peak_opt == 1: # Flatten Highland
			if terrain == "highland": r_list[7] = "plateau"
			if terrain == "alpine": r_list[7] = "highland"
		processed_regions.append(tuple(r_list))

	# Store the list for the debug sign placer
	_DEBUG_REGIONS = regions


	global plotgen
	plotgen = GeometricMultiFractal()
	return plotgen.generatePlotsByRegion(regions)


# -----------------------------------------------------------------------------
# Custom Climate Generation
# -----------------------------------------------------------------------------
_CLIMATE_ENGINE = None

def get_climate_engine():
	global _CLIMATE_ENGINE
	if _CLIMATE_ENGINE is None:
		m = CyMap()
		iW = m.getGridWidth()
		iH = m.getGridHeight()
		
		# Always fetch the fresh custom option and climate ID
		accuracy = m.getCustomMapOption(0)
		
		manager = CustomClimateManager(m)
		_CLIMATE_ENGINE = CustomClimateGenerator(manager, iW, iH, accuracy)
		
	return _CLIMATE_ENGINE

class ClimateDriver:
	"""
	Data structure representing a single climate influence vector.
	target: "TEMP" or "MOISTURE"
	type: "LINEAR", "MIRRORED", "RADIAL"
	origin: Tuple (cX, cY)
	start_val: Float. Influence at the origin.
	end_val: Float. Influence at the radius boundary.
	radius: Float. The distance of the transition.
	angle: Rotation of the vector (for Linear/Mirrored).
	"""
	def __init__(self, target, type, origin, start_val, end_val, radius, angle=0.0):
		self.target = target
		self.type = type
		self.origin = origin
		self.start_val = start_val
		self.end_val = end_val
		self.radius = radius
		self.angle = angle

class CustomClimateGenerator:
	"""
	The engine that processes a specific X, Y coordinate against the Driver Stack.
	"""
	def __init__(self, manager, iW, iH, accuracy):
		self.manager = manager
		self.iW = float(iW)
		self.iH = float(iH)
		self.accuracy = accuracy
		
		# Initialize fractal noise for jitter (Increased grain for visible scatter)
		gc = CyGlobalContext()
		self.noise = CyFractal()
		self.noise.fracInit(int(iW), int(iH), 3, gc.getGame().getMapRand(), 0, -1, -1)

	def get_climate_at(self, iX, iY):
		fx = float(iX) / self.iW
		fy = float(iY) / self.iH
		
		temp = self.manager.base_temp
		moisture = self.manager.base_moisture
		
		for driver in self.manager.drivers:
			# Vector from driver origin to current plot
			dx = fx - driver.origin[0]
			dy = fy - driver.origin[1]
			
			# 1. Determine Distance Factor (0.0 to 1.0)
			factor = 1.1 # Default to "Outside Radius"
			
			if driver.type == "RADIAL":
				dist = math.sqrt(dx*dx + dy*dy)
				factor = dist / driver.radius
				
			else: # LINEAR or MIRRORED
				rad = math.radians(driver.angle)
				cosA, sinA = math.cos(rad), math.sin(rad)
				
				# Dot Product: Projects the distance vector onto the angle's direction
				proj_dist = (dx * cosA) + (dy * sinA)
				
				if driver.type == "LINEAR":
					# Tiles behind the origin are outside the linear influence.
					if proj_dist >= 0:
						factor = proj_dist / driver.radius
						
				elif driver.type == "MIRRORED":
					# Symmetrical falloff on both sides of the axis
					factor = abs(proj_dist) / driver.radius
			
			# 2. Only apply if within radius
			if factor <= 1.0:
				# Linear Interpolation: Start + (Percentage * Difference)
				val_change = driver.start_val + (factor * (driver.end_val - driver.start_val))
				
				if driver.target == "TEMP":
					temp += val_change
				elif driver.target == "MOISTURE":
					moisture += val_change
				
		# --- Fractal Noise / Jitter Section ---
		# (Keep your existing jitter logic here...)
		offset_X = (iX + 50) % int(self.iW)
		offset_Y = (iY + 50) % int(self.iH)
		noise_t = (float(self.noise.getHeight(iX, iY)) / 255.0) - 0.5
		noise_m = (float(self.noise.getHeight(offset_X, offset_Y)) / 255.0) - 0.5
		
		noise_mult = 0.25 
		if self.accuracy == 1: noise_mult = 0.25
		elif self.accuracy == 2: noise_mult = 0.3 
			
		temp += (noise_t * noise_mult)
		moisture += (noise_m * noise_mult)
		
		# Final Clamp to 0.0 - 1.0
		if temp < 0.0: temp = 0.0
		if temp > 1.0: temp = 1.0
		if moisture < 0.0: moisture = 0.0
		if moisture > 1.0: moisture = 1.0
		
		return temp, moisture

class CustomClimateManager:
	"""
	Holds the Driver Stack. You can define multiple profiles here and select
	them based on map options or climate settings.
	"""
	def __init__(self, map_obj):
		self.map = map_obj
		self.drivers = []
		self.base_temp = 0.3
		self.base_moisture = 0.3
		
		# Load the profile
		self.setup_profile()

	def setup_profile(self):
		"""
		Set climate drivers here.
		Note: In Civ4, Y=0.0 is the South (bottom), Y=1.0 is the North (top).
		"""
		gc = CyGlobalContext()
		m = CyMap()
		iClimateIndex = m.getClimate()
		climate_info = gc.getClimateInfo(iClimateIndex)
		climate_type = climate_info.getType() # e.g., "CLIMATE_TROPICAL"

		# Initialize Base Values (Temperate Defaults)
		self.base_temp = 0.3
		self.base_moisture = 0.25
		
		# Apply Climate selection modifiers
		if climate_type == "CLIMATE_TROPICAL":
			self.base_temp = 0.6
			self.base_moisture = 0.4
			
		elif climate_type == "CLIMATE_COLD":
			self.base_temp = -0.2
			self.base_moisture = 0.3
			
		elif climate_type == "CLIMATE_ARID":
			self.base_temp = 0.4
			self.base_moisture = 0
			

		# 1. TEMPERATURE DRIVERS
		# Format: (target, type, origin, start_val, end_val, radius/distance, angle)
		# Base temperature gradient
		self.drivers.append(ClimateDriver("TEMP", "LINEAR", (0.5, 1.0), 1.0 , 0.0, 1, -90))
		
		# 2. MOISTURE DRIVERS
		# Central Desert
		self.drivers.append(ClimateDriver("MOISTURE", "RADIAL", (0.35, 0.55), -0.5, 0.0, 0.2))
		self.drivers.append(ClimateDriver("MOISTURE", "RADIAL", (0.18, 0.6), -0.5, 0.0, 0.15))

		# Winds from NE
		self.drivers.append(ClimateDriver("MOISTURE", "LINEAR", (1.0, .7), 1.0, 0.3, 0.35, -170))
		
		# winds from SE
		self.drivers.append(ClimateDriver("MOISTURE", "LINEAR", (0.9, 0.0), 1, 0.1, 0.55, 140))
		
		# Winds from SW
		self.drivers.append(ClimateDriver("MOISTURE", "LINEAR", (0, 0.2), 0.7, 0.3, 0.2, 30))
		
		# Jungles/Rainforests in North
		self.drivers.append(ClimateDriver("MOISTURE", "RADIAL", (0.2, 1), 1.7, 0.0, 0.4))
		self.drivers.append(ClimateDriver("MOISTURE", "RADIAL", (0.7, 1), 1.6, 0, 0.45))

# -----------------------------------------------------------------------------
# Terrain & Feature Generation (Downstream of Climate Gen)
# -----------------------------------------------------------------------------
TEMP_THRESHOLDS = [0.10, 0.20, 0.75]
MOISTURE_THRESHOLDS = [0.20, 0.45, 0.70]

# Rows = Temperature (0:Arctic, 1:Cold, 2:Temperate, 3:Tropical)
# Cols = Moisture (0:Arid, 1:Dry, 2:Humid, 3:Wet)
BIOME_TABLE = [
	["Snow", "Snow", "Snow", "Tundra"],
	["Snow", "Tundra", "Tundra", [("Tundra", 80), ("Grassland", 20)]],
	["Desert", [("Desert", 40), ("Plains", 60)], [("Plains", 30), ("Grassland", 70)], "Grassland"],
	["Desert", [("Desert", 40), ("Plains", 60)], [("Plains", 30), ("Grassland", 70)], "Grassland"]
]

FEATURE_TABLE = [
	[None, None, None, "Snow"],
	[None, None, "Snow", [("Snow", 60), ("Pine", 40)]],
	[None, None, [("Deciduous", 30), ("Pine", 70)], [("Deciduous", 70), ("Pine", 30)]],
	[None, "Deciduous", [("Deciduous", 70), ("Jungle", 30)], [("Deciduous", 20), ("Jungle", 80)]]
]

def _get_climate_band(value, thresholds):
	i = 0
	while i < len(thresholds):
		if value < thresholds[i]:
			return i
		i += 1
	return len(thresholds)

def _resolve_table_entry(entry, mapRand, log_label):
	if entry is None:
		return None

	if isinstance(entry, list):
		if len(entry) == 0:
			return None

		first = entry[0]
		if isinstance(first, tuple):
			total = 0
			for item, weight in entry:
				total += weight

			if total <= 0:
				return None

			roll = mapRand.get(total, log_label)
			running = 0
			for item, weight in entry:
				running += weight
				if roll < running:
					return item
			return entry[len(entry) - 1][0]

		roll = mapRand.get(len(entry), log_label)
		return entry[roll]

	return entry

class TerrainGenerator(CvMapGeneratorUtil.TerrainGenerator):
	def __init__(self, fGrassMoistureThreshold=0.5, fDesertMoistureThreshold=0.2):
		# We call the parent but we will use our own logic in generateTerrainAtPlot
		CvMapGeneratorUtil.TerrainGenerator.__init__(self)
		self.fGrassThreshold = fGrassMoistureThreshold
		self.fDesertThreshold = fDesertMoistureThreshold
		self.terrainMap = {
			"Snow": self.gc.getInfoTypeForString("TERRAIN_SNOW"),
			"Tundra": self.gc.getInfoTypeForString("TERRAIN_TUNDRA"),
			"Plains": self.gc.getInfoTypeForString("TERRAIN_PLAINS"),
			"Desert": self.gc.getInfoTypeForString("TERRAIN_DESERT"),
			"Grassland": self.gc.getInfoTypeForString("TERRAIN_GRASS")
		}

	def generateTerrainAtPlot(self, iX, iY):
		pPlot = self.map.plot(iX, iY)
		
		# 1. Handle Water (Early Exit)
		if pPlot.isWater():
			return pPlot.getTerrainType()

		# 2. Fetch climate
		engine = get_climate_engine()
		temp, moisture = engine.get_climate_at(iX, iY)

		temp_band = _get_climate_band(temp, TEMP_THRESHOLDS)
		moisture_band = _get_climate_band(moisture, MOISTURE_THRESHOLDS)
		terrain_name = _resolve_table_entry(BIOME_TABLE[temp_band][moisture_band], self.mapRand, "Terrain Table")

		if self.terrainMap.has_key(terrain_name):
			return self.terrainMap[terrain_name]
		return pPlot.getTerrainType()

def generateTerrainTypes():
	NiTextOut("Generating Terrain (Python Central Plains) ...")
	
	# We no longer need iDesertPercent or iPlainsPercent because we
	# define the climate via the piecewise moisture gradient.
	# We only pass the thresholds for the terrain bands.
	
	terraingen = TerrainGenerator(
		fGrassMoistureThreshold = 0.5, 
		fDesertMoistureThreshold = 0.2
	)
	
	terrainTypes = terraingen.generateTerrain()
	return terrainTypes

class FeatureGenerator(CvMapGeneratorUtil.FeatureGenerator):
	def __init__(self, iJunglePercent=60, iForestPercent=40):
		CvMapGeneratorUtil.FeatureGenerator.__init__(self, iJunglePercent, iForestPercent)
		
		self.gc = CyGlobalContext()
		self.terrainDesert = self.gc.getInfoTypeForString("TERRAIN_DESERT")
		self.terrainPlains = self.gc.getInfoTypeForString("TERRAIN_PLAINS")
		self.terrainGrass = self.gc.getInfoTypeForString("TERRAIN_GRASS")
		self.featureFloodPlains = self.gc.getInfoTypeForString("FEATURE_FLOOD_PLAINS")
		
		# Initialize fractal for moisture noise
		self.moisture_noise = CyFractal()
		self.moisture_noise.fracInit(self.iGridW, self.iGridH, 3, self.mapRand, 0, -1, -1)

	def addIceAtPlot(self, pPlot, iX, iY, lat):
		# Do nothing - prevents ice placement
		pass

	def addClimateFeature(self, pPlot, feature_name):
		if feature_name is None:
			return False

		if feature_name == "Jungle":
			if self.mapRand.get(100, "J") < self.iJunglePercent:
				if pPlot.canHaveFeature(self.featureJungle):
					pPlot.setFeatureType(self.featureJungle, -1)
					return True
			return False

		iVariety = -1
		if feature_name == "Deciduous":
			iVariety = 0
		elif feature_name == "Pine":
			iVariety = 1
		elif feature_name == "Snow":
			iVariety = 2
		else:
			return False

		if self.mapRand.get(100, "F") < self.iForestPercent:
			if pPlot.canHaveFeature(self.featureForest):
				pPlot.setFeatureType(self.featureForest, iVariety)
				return True

		return False

	def addFeaturesAtPlot(self, iX, iY):
		pPlot = self.map.sPlot(iX, iY)
		if pPlot.isWater() or pPlot.getFeatureType() != -1: return

		engine = get_climate_engine()
		temp, moisture = engine.get_climate_at(iX, iY)

		temp_band = _get_climate_band(temp, TEMP_THRESHOLDS)
		moisture_band = _get_climate_band(moisture, MOISTURE_THRESHOLDS)
		feature_name = _resolve_table_entry(FEATURE_TABLE[temp_band][moisture_band], self.mapRand, "Feature Table")

		if self.addClimateFeature(pPlot, feature_name):
			return

		# 3. Desert Features
		if pPlot.getTerrainType() == self.terrainDesert:
			if pPlot.isRiver():
				# Floodplains only go on Desert tiles with no other features
				if pPlot.getFeatureType() == -1:
					if pPlot.canHaveFeature(self.featureFloodPlains):
						pPlot.setFeatureType(self.featureFloodPlains, -1)
			if self.mapRand.get(100, "O") < 5:
				if pPlot.canHaveFeature(self.featureOasis):
					pPlot.setFeatureType(self.featureOasis, -1)

def addFeatures():
	NiTextOut("Adding Features (Python Central Plains) ...")
	featuregen = FeatureGenerator()
	featuregen.addFeatures()
	# expandCoastToTwoTiles()
	
	# Debug for fractal regions
	global _DEBUG_REGIONS
	# if _DEBUG_REGIONS:
		# _add_region_signs(_DEBUG_REGIONS)
	
	return 0

# -----------------------------------------------------------------------------
# Coast distance
# -----------------------------------------------------------------------------
def expandCoastToTwoTiles():
	"""Convert all water tiles within a BFC (Big Fat Cross) radius of land to coast."""
	map = CyMap()
	gc = CyGlobalContext()
	iW = map.getGridWidth()
	iH = map.getGridHeight()
	coast_id = gc.getInfoTypeForString("TERRAIN_COAST")

	# Collect all land plots
	land_plots = []
	for x in range(iW):
		for y in range(iH):
			if not map.plot(x, y).isWater():
				land_plots.append((x, y))

	# Mark water plots within BFC range
	coast_plots = set()
	for lx, ly in land_plots:
		for dx in range(-2, 3):
			for dy in range(-2, 3):
				# BFC Logic: Skip the four corner tiles of the 5x5 area
				# (where both dx and dy are 2 or -2)
				if abs(dx) == 2 and abs(dy) == 2:
					continue
				
				nx = lx + dx
				ny = ly + dy
				
				# Check bounds
				if 0 <= nx < iW and 0 <= ny < iH:
					pPlot = map.plot(nx, ny)
					if pPlot.isWater():
						coast_plots.add((nx, ny))

	# Apply coast terrain
	for x, y in coast_plots:
		map.plot(x, y).setTerrainType(coast_id, True, True)
		

# -----------------------------------------------------------------------------
# River Generator
# -----------------------------------------------------------------------------
class RiverGenerator:
	"""
	From Tectonics.py class riversFromSea.
	Added to generate more natural-looking rivers.
	Input exclude_rects to prevent river generation in certain regions (used for Sahara in this mapscript).
	"""
	def __init__(self, river_density=1.0, exclude_rects=None, reduce_rects=None, survival_chance=20):
		"""
		exclude_rects: list of (west, south, width, height) – rivers never start or flow here.
		reduce_rects: list of (west, south, width, height) – rivers have only `survival_chance`% chance to flow here.
		river_density: float > 0; 1.0 gives a moderate number of rivers (similar to old divider=2).
		"""
		self.gc = CyGlobalContext()
		self.dice = self.gc.getGame().getMapRand()
		self.map = CyMap()
		self.width = self.map.getGridWidth()
		self.height = self.map.getGridHeight()
		self.straightThreshold = 3
		if (self.width * self.height > 400):
			self.straightThreshold = 2
		self.survival_chance = survival_chance
		self.river_density = river_density

		# Convert exclude rectangles
		self.exclude_rects = []
		if exclude_rects:
			for (west, south, width, height) in exclude_rects:
				west_x = int(self.width * west)
				east_x = int(self.width * (west + width))
				south_y = int(self.height * south)
				north_y = int(self.height * (south + height))
				self.exclude_rects.append((west_x, east_x, south_y, north_y))

		# Convert reduce rectangles
		self.reduce_rects = []
		if reduce_rects:
			for (west, south, width, height) in reduce_rects:
				west_x = int(self.width * west)
				east_x = int(self.width * (west + width))
				south_y = int(self.height * south)
				north_y = int(self.height * (south + height))
				self.reduce_rects.append((west_x, east_x, south_y, north_y))

	def is_excluded(self, x, y):
		for (west_x, east_x, south_y, north_y) in self.exclude_rects:
			if west_x <= x <= east_x and south_y <= y <= north_y:
				return True
		return False

	def is_reduced(self, x, y):
		"""Return True if the plot lies in a reduce_rect; also roll for chance."""
		for (west_x, east_x, south_y, north_y) in self.reduce_rects:
			if west_x <= x <= east_x and south_y <= y <= north_y:
				# Roll the dice: return True if the roll is < survival_chance (i.e., allowed)
				return self.dice.get(100, "River reduction") < self.survival_chance
		return True   # not in any reduce_rect -> always allowed

	def collateCoasts(self):
		"""Return list of land plots adjacent to a large water body."""
		result = []
		for x in range(self.width):
			for y in range(self.height):
				plot = self.map.plot(x, y)
				if plot.isCoastalLand():
					# Check if any adjacent water plot is large enough
					for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
						nx, ny = x+dx, y+dy
						if 0 <= nx < self.width and 0 <= ny < self.height:
							adj = self.map.plot(nx, ny)
							if self.is_water_for_river(adj):
								result.append(plot)
								break
		return result

	def seedRivers(self):
		# Base number of rivers proportional to the map's perimeter (width+height)
		# For density 1.0, this gives about the same as the old divider=2.
		base = (self.width + self.height) / 2.0
		riversNumber = int(base * self.river_density) + 1

		self.coasts = self.collateCoasts()
		coastsNumber = len(self.coasts)
		if coastsNumber == 0:
			return

		# Cap to the number of available coastal plots to avoid excessive attempts
		riversNumber = min(riversNumber, coastsNumber)

		coastShare = coastsNumber / riversNumber
		for i in range(riversNumber):
			for attempt in range(50):
				choiceCoast = coastShare * i + self.dice.get(coastShare, "Pick a coast for the river")
				if choiceCoast >= coastsNumber:
					choiceCoast = coastsNumber - 1
				plot = self.coasts[choiceCoast]
				x, y = plot.getX(), plot.getY()
				# Skip if excluded OR (reduced and dice fails)
				if self.is_excluded(x, y):
					continue
				if not self.is_reduced(x, y):
					continue
				(x, y, flow) = self.generateRiverFromPlot(plot, x, y)
				if flow != CardinalDirectionTypes.NO_CARDINALDIRECTION:
					riverID = self.gc.getMap().getNextRiverID()
					self.addRiverFrom(x, y, flow, riverID)
				break

	def canFlowFrom(self, plot, upperPlot):
		"""Return True if water can flow from `plot` to `upperPlot`."""
		if self.is_water_for_river(plot):
			return False
		if plot.getPlotType() == PlotTypes.PLOT_PEAK:
			return False
		# If the upper plot is in an excluded rectangle, stop
		ux, uy = upperPlot.getX(), upperPlot.getY()
		if self.is_excluded(ux, uy):
			return False
		# If the upper plot is in a reduced rectangle, apply chance
		if not self.is_reduced(ux, uy):
			return False

		if plot.getPlotType() == PlotTypes.PLOT_HILLS:
			return True
		if plot.getPlotType() == PlotTypes.PLOT_LAND:
			if self.is_water_for_river(upperPlot):
				return False
			return True
		return False

	def is_water_for_river(self, plot):
		"""Return True only if the plot is water and its area is large enough."""
		if not plot.isWater():
			return False
		area_id = plot.getArea()
		if area_id == -1:
			return False
		area = self.map.getArea(area_id)
		return area.getNumTiles() >= 5   # min_water_area_size fixed at 5

	def generateRiverFromPlot(self, plot, x, y):
		FlowDirection = CardinalDirectionTypes.NO_CARDINALDIRECTION
		if ((y < 1 or y >= self.height - 1) or plot.isNOfRiver() or plot.isWOfRiver()):
			return (x, y, FlowDirection)
		eastX = self.eastX(x)
		westX = self.westX(x)
		otherPlot = True
		eastPlot = self.map.plot(eastX, y)
		if eastPlot.isCoastalLand():
			# Check water using is_water_for_river
			if (self.is_water_for_river(self.map.plot(x, y+1)) or
				self.is_water_for_river(self.map.plot(eastX, y+1))):
				landPlot1 = self.map.plot(x, y-1)
				landPlot2 = self.map.plot(eastX, y-1)
				if landPlot1.isWater() or landPlot2.isWater():
					otherPlot = True
				else:
					FlowDirection = CardinalDirectionTypes.CARDINALDIRECTION_NORTH
					otherPlot = False
			if otherPlot:
				if (self.is_water_for_river(self.map.plot(x, y-1)) or
					self.is_water_for_river(self.map.plot(eastX, y-1))):
					landPlot1 = self.map.plot(x, y+1)
					landPlot2 = self.map.plot(eastX, y+1)
					if landPlot1.isWater() or landPlot2.isWater():
						otherPlot = True
					else:
						FlowDirection = CardinalDirectionTypes.CARDINALDIRECTION_SOUTH
						otherPlot = False
		if otherPlot:
			southPlot = self.map.plot(x, y-1)
			if southPlot.isCoastalLand():
				if (self.is_water_for_river(self.map.plot(eastX, y)) or
					self.is_water_for_river(self.map.plot(eastX, y-1))):
					landPlot1 = self.map.plot(westX, y)
					landPlot2 = self.map.plot(westX, y-1)
					if landPlot1.isWater() or landPlot2.isWater():
						otherPlot = True
					else:
						FlowDirection = CardinalDirectionTypes.CARDINALDIRECTION_EAST
						otherPlot = False
				if otherPlot:
					if (self.is_water_for_river(self.map.plot(westX, y)) or
						self.is_water_for_river(self.map.plot(westX, y-1))):
						landPlot1 = self.map.plot(eastX, y)
						landPlot2 = self.map.plot(eastX, y-1)
						if landPlot1.isWater() or landPlot2.isWater():
							otherPlot = True
						else:
							FlowDirection = CardinalDirectionTypes.CARDINALDIRECTION_WEST
		return (x, y, FlowDirection)

	def addRiverFrom(self, x, y, flow, riverID):
		plot = self.map.plot(x, y)
		if self.is_water_for_river(plot):
			return
		eastX = self.eastX(x)
		westX = self.westX(x)
		if self.preventRiversFromCrossing(x, y, flow, riverID):
			return
		plot.setRiverID(riverID)
		if (flow == CardinalDirectionTypes.CARDINALDIRECTION_WEST) or (flow == CardinalDirectionTypes.CARDINALDIRECTION_EAST):
			plot.setNOfRiver(True, flow)
		else:
			plot.setWOfRiver(True, flow)
		xShift = 0
		yShift = 0
		if flow == CardinalDirectionTypes.CARDINALDIRECTION_WEST:
			xShift = 1
		elif flow == CardinalDirectionTypes.CARDINALDIRECTION_EAST:
			xShift = -1
		elif flow == CardinalDirectionTypes.CARDINALDIRECTION_NORTH:
			yShift = -1
		elif flow == CardinalDirectionTypes.CARDINALDIRECTION_SOUTH:
			yShift = 1
		nextX = x + xShift
		nextY = y + yShift
		if nextX >= self.width:
			nextX = 0
		if nextY >= self.height:
			return
		nextPlot = self.map.plot(nextX, nextY)
		if not self.canFlowFrom(plot, nextPlot):
			return
		if plot.getTerrainType() == CyGlobalContext().getInfoTypeForString("TERRAIN_SNOW") and self.dice.get(10, "Stop on ice") > 3:
			return
		flatDesert = (plot.getPlotType() == PlotTypes.PLOT_LAND) and (plot.getTerrainType() == CyGlobalContext().getInfoTypeForString("TERRAIN_DESERT"))
		turnThreshold = 16
		if flatDesert:
			turnThreshold = 18
		turned = False
		northY = y + 1
		southY = y - 1
		if (flow == CardinalDirectionTypes.CARDINALDIRECTION_WEST) or (flow == CardinalDirectionTypes.CARDINALDIRECTION_EAST):
			if (northY < self.height) and (self.dice.get(20, "branch from north") > turnThreshold):
				if (self.canFlowFrom(plot, self.map.plot(x, northY)) and
					self.canFlowFrom(self.map.plot(self.eastX(x), y), self.map.plot(self.eastX(x), northY))):
					turned = True
					if flow == CardinalDirectionTypes.CARDINALDIRECTION_WEST:
						self.addRiverFrom(x, y, CardinalDirectionTypes.CARDINALDIRECTION_SOUTH, riverID)
					else:
						westPlot = self.map.plot(westX, y)
						westPlot.setRiverID(riverID)
						self.addRiverFrom(westX, y, CardinalDirectionTypes.CARDINALDIRECTION_SOUTH, riverID)
			if (not turned) and (southY >= 0) and (self.dice.get(20, "branch from south") > turnThreshold):
				if (self.canFlowFrom(plot, self.map.plot(x, southY)) and
					self.canFlowFrom(self.map.plot(self.eastX(x), y), self.map.plot(self.eastX(x), southY))):
					turned = True
					if flow == CardinalDirectionTypes.CARDINALDIRECTION_WEST:
						southPlot = self.map.plot(x, y-1)
						southPlot.setRiverID(riverID)
						self.addRiverFrom(x, southY, CardinalDirectionTypes.CARDINALDIRECTION_NORTH, riverID)
					else:
						westPlot = self.map.plot(westX, southY)
						westPlot.setRiverID(riverID)
						self.addRiverFrom(westX, southY, CardinalDirectionTypes.CARDINALDIRECTION_NORTH, riverID)
		else:
			if (self.canFlowFrom(plot, self.map.plot(eastX, y)) and
				self.canFlowFrom(self.map.plot(x, southY), self.map.plot(eastX, y)) and
				(self.dice.get(20, "branch from east") > turnThreshold)):
				turned = True
				if flow == CardinalDirectionTypes.CARDINALDIRECTION_NORTH:
					eastPlot = self.map.plot(eastX, y)
					eastPlot.setRiverID(riverID)
					self.addRiverFrom(eastX, y, CardinalDirectionTypes.CARDINALDIRECTION_WEST, riverID)
				else:
					northEastPlot = self.map.plot(eastX, y+1)
					northEastPlot.setRiverID(riverID)
					self.addRiverFrom(eastX, y+1, CardinalDirectionTypes.CARDINALDIRECTION_WEST, riverID)
			if (not turned) and (self.canFlowFrom(plot, self.map.plot(westX, y)) and
				self.canFlowFrom(self.map.plot(x, southY), self.map.plot(westX, southY)) and
				(self.dice.get(20, "branch from west") > turnThreshold)):
				turned = True
				if flow == CardinalDirectionTypes.CARDINALDIRECTION_NORTH:
					self.addRiverFrom(x, y, CardinalDirectionTypes.CARDINALDIRECTION_EAST, riverID)
				else:
					northPlot = self.map.plot(x, y+1)
					northPlot.setRiverID(riverID)
					self.addRiverFrom(x, y+1, CardinalDirectionTypes.CARDINALDIRECTION_EAST, riverID)
		spawnInDesert = (not turned) and flatDesert
		if (self.dice.get(10, "straight river") > self.straightThreshold) or spawnInDesert:
			self.addRiverFrom(nextX, nextY, flow, riverID)
		else:
			if not turned:
				plot = self.map.plot(nextX, nextY)
				if (plot.getPlotType() == PlotTypes.PLOT_LAND) and (self.dice.get(10, "Rivers start in hills") > 3):
					plot.setPlotType(PlotTypes.PLOT_HILLS, True, True)
					if (flow == CardinalDirectionTypes.CARDINALDIRECTION_WEST) or (flow == CardinalDirectionTypes.CARDINALDIRECTION_EAST):
						if southY > 0:
							self.map.plot(nextX, southY).setPlotType(PlotTypes.PLOT_HILLS, True, True)
					else:
						self.map.plot(eastX, nextY).setPlotType(PlotTypes.PLOT_HILLS, True, True)

	def preventRiversFromCrossing(self, x, y, flow, riverID):
		plot = self.map.plot(x, y)
		eastX = self.eastX(x)
		westX = self.westX(x)
		if (flow == CardinalDirectionTypes.CARDINALDIRECTION_WEST):
			if (plot.isNOfRiver()):
				return True
			if (self.map.plot(eastX, y).isNOfRiver()):
				return True
			southPlot = self.map.plot(x, y-1)
			if (southPlot.isWOfRiver() and southPlot.getRiverNSDirection() == CardinalDirectionTypes.CARDINALDIRECTION_SOUTH):
				return True
			if (plot.isWOfRiver() and plot.getRiverNSDirection() == CardinalDirectionTypes.CARDINALDIRECTION_NORTH):
				return True
			if (self.map.plot(eastX, y).isWater()):
				return True
			if (self.map.plot(x, y-1).isWater()):
				return True
			if (self.map.plot(eastX, y-1).isWater()):
				return True
		if (flow == CardinalDirectionTypes.CARDINALDIRECTION_EAST):
			if (plot.isNOfRiver()):
				return True
			if (self.map.plot(westX, y).isNOfRiver()):
				return True
			southPlot = self.map.plot(westX, y-1)
			if (southPlot.isWOfRiver() and southPlot.getRiverNSDirection() == CardinalDirectionTypes.CARDINALDIRECTION_SOUTH):
				return True
			westPlot = self.map.plot(westX, y)
			if (westPlot.isWOfRiver() and westPlot.getRiverNSDirection() == CardinalDirectionTypes.CARDINALDIRECTION_NORTH):
				return True
			if (self.map.plot(westX, y).isWater()):
				return True
			if (self.map.plot(x, y-1).isWater()):
				return True
			if (self.map.plot(westX, y-1).isWater()):
				return True
		if (flow == CardinalDirectionTypes.CARDINALDIRECTION_NORTH):
			if (plot.isWOfRiver()):
				return True
			eastPlot = self.map.plot(eastX, y)
			if (eastPlot.isNOfRiver() and eastPlot.getRiverWEDirection() == CardinalDirectionTypes.CARDINALDIRECTION_EAST):
				return True
			if (plot.isNOfRiver() and plot.getRiverWEDirection() == CardinalDirectionTypes.CARDINALDIRECTION_WEST):
				return True
			if (self.map.plot(x, y-1).isWOfRiver()):
				return True
			if (self.map.plot(x, y-1).isWater()):
				return True
			if (self.map.plot(x+1, y).isWater()):
				return True
			if (self.map.plot(x+1, y-1).isWater()):
				return True
		if (flow == CardinalDirectionTypes.CARDINALDIRECTION_SOUTH):
			if (plot.isWOfRiver()):
				return True
			eastPlot = self.map.plot(eastX, y+1)
			if (eastPlot.isNOfRiver() and eastPlot.getRiverWEDirection() == CardinalDirectionTypes.CARDINALDIRECTION_EAST):
				return True
			northPlot = self.map.plot(x, y+1)
			if (northPlot.isNOfRiver() and northPlot.getRiverWEDirection() == CardinalDirectionTypes.CARDINALDIRECTION_WEST):
				return True
			if (self.map.plot(x, y+1).isWOfRiver()):
				return True
			if (self.map.plot(x, y+1).isWater()):
				return True
			if (self.map.plot(x+1, y).isWater()):
				return True
			if (self.map.plot(x+1, y+1).isWater()):
				return True
		return False

	def westX(self, x):
		westX = x - 1
		if (westX < 0):
			westX = self.width
		return westX

	def eastX(self, x):
		eastX = x + 1
		if (eastX >= self.width):
			eastX = 0
		return eastX
		

# -----------------------------------------------------------------------------
# Custom River Generator
# -----------------------------------------------------------------------------
"""Custom generator for drawing rivers / waterways running through specified coordinates."""
class PathNavigator:
	def __init__(self, map, dice):
		self.map = map
		self.dice = dice
		self.iW = map.getGridWidth()
		self.iH = map.getGridHeight()
		self.noise = CyFractal()
		self.noise.fracInit(self.iW, self.iH, 2, self.dice, 0, -1, -1)
		self.size_factor = float(self.iW + self.iH) / 64.0

	def is_ocean(self, x, y):
		if x < 0 or x >= self.iW or y < 0 or y >= self.iH: return False
		pPlot = self.map.plot(x, y)
		if pPlot.isWater():
			pArea = pPlot.area()
			if pArea:
				if pArea.getNumTiles() >= 10: return True
		return False

	def is_any_water(self, x, y):
		if x < 0 or x >= self.iW or y < 0 or y >= self.iH: return False
		return self.map.plot(x, y).isWater()

	def get_best_move(self, cx, cy, tx, ty, visited, is_water_path, meander):
		best_score = 999999.0
		best_move = None
		accuracy = self.map.getCustomMapOption(0)
		dist_to_target = math.sqrt((cx - tx)**2 + (cy - ty)**2)

		if is_water_path:
			moves = [(1,0), (-1,0), (0,1), (0,-1)]
		else:
			moves = [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)]
			
		for move in moves:
			nx, ny = cx + move[0], cy + move[1]
			if nx < 0 or nx >= self.iW or ny < 0 or ny >= self.iH: continue
			
			bVisited = False
			for v in visited:
				if nx == v[0] and ny == v[1]:
					bVisited = True
					break
			if bVisited: continue
			
			if is_water_path:
				bSkip2x2 = False
				if accuracy == 2 or dist_to_target < 4:
					bSkip2x2 = True
				else:
					for adj in [(1,0), (-1,0), (0,1), (0,-1)]:
						if self.is_ocean(nx + adj[0], ny + adj[1]):
							bSkip2x2 = True
							break
				
				if not bSkip2x2:
					if self.is_any_water(nx-1, ny) and self.is_any_water(nx, ny-1) and self.is_any_water(nx-1, ny-1): continue
					if self.is_any_water(nx+1, ny) and self.is_any_water(nx, ny-1) and self.is_any_water(nx+1, ny-1): continue
					if self.is_any_water(nx-1, ny) and self.is_any_water(nx, ny+1) and self.is_any_water(nx-1, ny+1): continue
					if self.is_any_water(nx+1, ny) and self.is_any_water(nx, ny+1) and self.is_any_water(nx+1, ny+1): continue

			dist = math.sqrt((nx - tx)**2 + (ny - ty)**2)
			n_val = (self.noise.getHeight(nx, ny) / 100.0) - 0.5
			score = dist * (1.0 + (n_val * meander))
			
			if score < best_score:
				best_score = score
				best_move = (nx, ny, move[0], move[1])
		return best_move

	def generate_path(self, start, end, meander, is_water_path):
		curr_x, curr_y = start
		path = [(curr_x, curr_y)]
		visited = [(curr_x, curr_y)]
		
		max_steps = (abs(curr_x - end[0]) + abs(curr_y - end[1])) * 4
		for i in range(max_steps):
			if curr_x == end[0] and curr_y == end[1]: break
			move = self.get_best_move(curr_x, curr_y, end[0], end[1], visited, is_water_path, meander)
			if not move: break
			curr_x, curr_y = move[0], move[1]
			path.append((curr_x, curr_y))
			visited.append((curr_x, curr_y))
			
			if is_water_path:
				if self.is_ocean(curr_x, curr_y):
					break
			else:
				# Standard River: Stop if we hit ANY water
				# We skip i=0 to allow rivers to start adjacent to water
				if i > 0:
					if self.is_any_water(curr_x, curr_y):
						break
		return path
	
class WaterwayMaker:
	def __init__(self, navigator):
		self.nav = navigator
		self.map = navigator.map

	def build(self, checkpoints, meander, bridge_spacing, bBridgesEnabled=True):
		full_path = []
		for i in range(len(checkpoints) - 1):
			start = (int(self.nav.iW * checkpoints[i][0]), int(self.nav.iH * checkpoints[i][1]))
			end = (int(self.nav.iW * checkpoints[i+1][0]), int(self.nav.iH * checkpoints[i+1][1]))
			segment = self.nav.generate_path(start, end, meander, True)
			if i == 0:
				full_path.extend(segment)
			else:
				full_path.extend(segment[1:])
			if segment:
				if self.nav.is_ocean(segment[-1][0], segment[-1][1]):
					break
		
		self._apply_to_map(full_path, bridge_spacing, bBridgesEnabled)

	def _apply_to_map(self, path, bridge_spacing, bBridgesEnabled):
		if not path: return
		riverID = self.map.getNextRiverID()
		self.map.incrementNextRiverID()
		step_count = 0
		next_gap = int((self.nav.dice.get(3, "G") + bridge_spacing) * self.nav.size_factor)
		if next_gap < 2: next_gap = 2

		for i in range(len(path)):
			x, y = path[i]
			pPlot = self.map.plot(x, y)
			
			# Force Ocean on last tile or existing ocean
			if i == len(path) - 1 or self.nav.is_ocean(x, y):
				pPlot.setPlotType(PlotTypes.PLOT_OCEAN, True, True)
				step_count = 0
				continue

			bIsBridge = False
			# Only evaluate bridge logic if bBridgesEnabled is True
			if bBridgesEnabled:
				if step_count >= next_gap:
					bNearOcean = False
					for adj in [(1,0), (-1,0), (0,1), (0,-1)]:
						if self.nav.is_ocean(x+adj[0], y+adj[1]):
							bNearOcean = True
							break
					if not bNearOcean:
						bIsBridge = True

			if bIsBridge:
				pPlot.setPlotType(PlotTypes.PLOT_LAND, True, True)
				pPlot.setFeatureType(FeatureTypes.NO_FEATURE, -1)
				
				# Flatten 8-way adjacent peaks
				for adj_x in range(-1, 2):
					for adj_y in range(-1, 2):
						if adj_x == 0 and adj_y == 0: continue
						nx, ny = x + adj_x, y + adj_y
						if nx >= 0 and nx < self.nav.iW and ny >= 0 and ny < self.nav.iH:
							pAdj = self.map.plot(nx, ny)
							if pAdj.getPlotType() == PlotTypes.PLOT_PEAK:
								pAdj.setPlotType(PlotTypes.PLOT_HILLS, True, True)
				
				dx, dy, ndx, ndy = 0, 0, 0, 0
				if i > 0: dx, dy = x - path[i-1][0], y - path[i-1][1]
				if i < len(path)-1: ndx, ndy = path[i+1][0] - x, path[i+1][1] - y
				self._apply_bridge_flags(x, y, dx, dy, ndx, ndy, riverID)
				step_count = 0
				next_gap = int((self.nav.dice.get(3, "G") + bridge_spacing) * self.nav.size_factor)
				if next_gap < 2: next_gap = 2
			else:
				pPlot.setPlotType(PlotTypes.PLOT_OCEAN, True, True)
				step_count += 1

	def _apply_bridge_flags(self, x, y, dx, dy, ndx, ndy, rID):
		N, S, E, W = CardinalDirectionTypes.CARDINALDIRECTION_NORTH, CardinalDirectionTypes.CARDINALDIRECTION_SOUTH, CardinalDirectionTypes.CARDINALDIRECTION_EAST, CardinalDirectionTypes.CARDINALDIRECTION_WEST
		corner = "STRAIGHT"
		if dy==1 and ndx==1: corner="S_E"
		elif dy==1 and ndx==-1: corner="S_W"
		elif dy==-1 and ndx==1: corner="N_E"
		elif dy==-1 and ndx==-1: corner="N_W"
		elif dx==-1 and ndy==-1: corner="E_S"
		elif dx==1 and ndy==-1: corner="W_S"
		elif dx==-1 and ndy==1: corner="E_N"
		elif dx==1 and ndy==1: corner="W_N"

		if corner == "STRAIGHT":
			p = self.map.plot(x, y)
			if dx != 0:
				flow = E
				if dx != 1: flow = W
				p.setNOfRiver(True, flow)
			elif dy != 0:
				flow = N
				if dy != 1: flow = S
				p.setWOfRiver(True, flow)
			p.setRiverID(rID)
		elif corner == "S_E":
			p=self.map.plot(x-1, y); p.setWOfRiver(True, N); p.setRiverID(rID)
			p=self.map.plot(x, y+1); p.setNOfRiver(True, E); p.setRiverID(rID)
		elif corner == "S_W":
			p=self.map.plot(x, y); p.setWOfRiver(True, N); p.setRiverID(rID)
			p=self.map.plot(x, y+1); p.setNOfRiver(True, W); p.setRiverID(rID)
		elif corner == "N_E":
			p=self.map.plot(x-1, y); p.setWOfRiver(True, S); p.setRiverID(rID)
			p=self.map.plot(x, y); p.setNOfRiver(True, E); p.setRiverID(rID)
		elif corner == "N_W":
			p=self.map.plot(x, y); p.setWOfRiver(True, S); p.setNOfRiver(True, W); p.setRiverID(rID)
		elif corner == "E_S":
			p=self.map.plot(x-1, y); p.setWOfRiver(True, S); p.setRiverID(rID)
			p=self.map.plot(x, y+1); p.setNOfRiver(True, W); p.setRiverID(rID)
		elif corner == "W_S":
			# --- INCORPORATED YOUR FIX ---
			p=self.map.plot(x, y); p.setWOfRiver(True, S); p.setRiverID(rID)
			p=self.map.plot(x, y+1); p.setNOfRiver(True, E); p.setRiverID(rID)
		elif corner == "E_N":
			p=self.map.plot(x-1, y); p.setWOfRiver(True, N); p.setRiverID(rID)
			p=self.map.plot(x, y); p.setNOfRiver(True, W); p.setRiverID(rID)
		elif corner == "W_N":
			p=self.map.plot(x, y); p.setWOfRiver(True, N); p.setNOfRiver(True, E); p.setRiverID(rID)

class StandardRiverMaker:
	def __init__(self, navigator):
		self.nav = navigator
		self.map = navigator.map

	def build(self, checkpoints, meander):
		riverID = self.map.getNextRiverID()
		self.map.incrementNextRiverID()
		for i in range(len(checkpoints) - 1):
			start = (int(self.nav.iW * checkpoints[i][0]), int(self.nav.iH * checkpoints[i][1]))
			end = (int(self.nav.iW * checkpoints[i+1][0]), int(self.nav.iH * checkpoints[i+1][1]))
			path = self.nav.generate_path(start, end, meander, False)
			if not path: break
			
			for j in range(len(path)-1):
				curr, next = path[j], path[j+1]
				dx, dy = next[0]-curr[0], next[1]-curr[1]
				bStop = self._apply_river_flags(curr[0], curr[1], dx, dy, riverID)
				if bStop: return

	def _apply_river_flags(self, x, y, dx, dy, rID):
		N, S, E, W = CardinalDirectionTypes.CARDINALDIRECTION_NORTH, CardinalDirectionTypes.CARDINALDIRECTION_SOUTH, CardinalDirectionTypes.CARDINALDIRECTION_EAST, CardinalDirectionTypes.CARDINALDIRECTION_WEST
		bStop = False
		
		# Horizontal
		if dx != 0:
			if dx == 1:
				tx = x
				flow = E
				look_x = tx + 1
			else:
				tx = x - 1
				flow = W
				look_x = tx - 1
			
			# Stop at ANY water (Lake or Coast)
			if self.nav.is_any_water(look_x, y) or self.nav.is_any_water(look_x, y-1):
				bStop = True
			
			p = self.map.plot(tx, y)
			if p:
				if not self.nav.is_any_water(tx, y):
					if not self.nav.is_any_water(tx, y-1):
						if self._check_merge(tx, y, False, flow): 
							bStop = True
						p.setNOfRiver(True, flow)
						p.setRiverID(rID)
			if bStop: return True

		# Vertical
		if dy != 0:
			tx = x + dx - 1
			if dy == 1:
				ty = y
				flow = N
				look_y = ty + 1
			else:
				ty = y - 1
				flow = S
				look_y = ty - 1
			
			# Stop at ANY water (Lake or Coast)
			if self.nav.is_any_water(tx, look_y) or self.nav.is_any_water(tx+1, look_y):
				bStop = True
				
			p = self.map.plot(tx, ty)
			if p:
				if not self.nav.is_any_water(tx, ty):
					if not self.nav.is_any_water(tx+1, ty):
						if self._check_merge(tx, ty, True, flow): 
							bStop = True
						p.setWOfRiver(True, flow)
						p.setRiverID(rID)
		return bStop

	def _check_merge(self, x, y, is_vertical, flow):
		N, S, E, W = CardinalDirectionTypes.CARDINALDIRECTION_NORTH, CardinalDirectionTypes.CARDINALDIRECTION_SOUTH, CardinalDirectionTypes.CARDINALDIRECTION_EAST, CardinalDirectionTypes.CARDINALDIRECTION_WEST
		if is_vertical:
			if flow == N:
				p=self.map.plot(x, y+1)
				if p and ((p.isWOfRiver() and p.getRiverNSDirection()==N) or (p.isNOfRiver() and p.getRiverWEDirection()==W)): return True
				p=self.map.plot(x+1, y+1)
				if p and (p.isNOfRiver() and p.getRiverWEDirection()==E): return True
			else:
				p=self.map.plot(x, y)
				if p and (p.isNOfRiver() and p.getRiverWEDirection()==W): return True
				p=self.map.plot(x, y-1)
				if p and (p.isWOfRiver() and p.getRiverNSDirection()==S): return True
				p=self.map.plot(x+1, y)
				if p and (p.isNOfRiver() and p.getRiverWEDirection()==E): return True
		else:
			if flow == E:
				p=self.map.plot(x, y)
				if p and (p.isWOfRiver() and p.getRiverNSDirection()==N): return True
				p=self.map.plot(x, y-1)
				if p and (p.isWOfRiver() and p.getRiverNSDirection()==S): return True
				p=self.map.plot(x+1, y)
				if p and (p.isNOfRiver() and p.getRiverWEDirection()==E): return True
			else: # W
				p=self.map.plot(x-1, y)
				if p and ((p.isNOfRiver() and p.getRiverWEDirection()==W) or (p.isWOfRiver() and p.getRiverNSDirection()==N)): return True
				p=self.map.plot(x-1, y-1)
				if p and (p.isWOfRiver() and p.getRiverNSDirection()==S): return True
		return False

def addRivers():
	"""Specify custom rivers here."""
	m = CyMap()
	m.recalculateAreas()
	gc = CyGlobalContext()
	dice = gc.getGame().getMapRand()
	
	# Initialize the new Class-based system
	nav = PathNavigator(m, dice)
	waterways = WaterwayMaker(nav)
	rivers = StandardRiverMaker(nav)
	
	# Fetch Map Options: 0=Disabled, 1=Regular, 2=Bridged Waterway, 3=Bridgeless
	river_opt = m.getCustomMapOption(2)
	is_waterway = (river_opt == 2 or river_opt == 3)
	has_bridges = (river_opt == 2)
	accuracy = m.getCustomMapOption(0)
	

	
	##################################################################################################
	# 1. Historical Rivers
	##################################################################################################
	if river_opt != 0:
		if accuracy == 0: # HIGH ACCURACY
			Tasmania_Derwent = [(0.614, 0.1), (0.67, 0.031)]
			Murray = [(0.653, 0.239), (0.581, 0.317), (0.475, 0.238)]
			Darling = [(0.733, 0.422), (0.68, 0.433), (0.589, 0.39), (0.56, 0.27)]
			WA_Swan_Avon = [(0.213, 0.315), (0.182, 0.36), (0.135, 0.326)]
			WA_Fortescue = [(0.194, 0.573), (0.208, 0.596), (0.111, 0.672)]
			WA_Fitzroy = [(0.32, 0.732), (0.275, 0.71), (0.23, 0.815)]
			NT_Ord = [(0.359, 0.762), (0.346, 0.878)]
			NQLD_Burdekin = [(0.629, 0.706), (0.668, 0.652), (0.701, 0.715)]
			QLD_Fitzroy = [(0.691, 0.578), (0.756, 0.622)]
			QLD_Warrego = [(0.632, 0.575), (0.632, 0.395)]

			rivers.build(Tasmania_Derwent, meander=0.2)
			rivers.build(Murray, meander=0.2)
			rivers.build(Darling, meander=0.2)
			rivers.build(WA_Swan_Avon, meander=0.2)
			rivers.build(WA_Fortescue, meander=0.2)
			rivers.build(WA_Fitzroy, meander=0.2)
			rivers.build(NT_Ord, meander=0.2)
			rivers.build(NQLD_Burdekin, meander=0.2)
			rivers.build(QLD_Fitzroy, meander=0.2)
			rivers.build(QLD_Warrego, meander=0.2)

		elif accuracy == 1: # Medium accuracy
			# YELLOW RIVER - Xian to Mouth
			yellow = [
				(0.015, 0.648),
				(0.109, 0.662), 
				(0.194, 0.86), 
				(0.353, 0.844), 
				(0.343, 0.5),   # Xi'an Junction
				(0.515, 0.513), # Zhengzhou
				(0.73, 0.73)    # Mouth
			]
			# LONG RIVER with random checkpoints
				# dice.get(21, ...) returns 0 to 20. 
				# (0 to 20 - 10) / 200.0 results in -0.05 to +0.05.
			# River Checkpoints (Base Y: 0.75)
			j1 = (float(dice.get(21, "Jitter 1")) - 10.0) / 200.0
			j2 = (float(dice.get(21, "Jitter 2")) - 10.0) / 200.0
			j3 = (float(dice.get(21, "Jitter 3")) - 10.0) / 200.0
			long_river = [(0.1, 0.25 + j1), (0.4, 0.25 + j2), (1.0, 0.25 + j3)]
			
			# set if waterway or regular river
			if is_waterway:
				waterways.build(long_river, meander=0.15, bridge_spacing=4, bBridgesEnabled=has_bridges)
				waterways.build(yellow, meander=0.2, bridge_spacing=4, bBridgesEnabled=has_bridges)
				
			else:
				rivers.build(long_river, meander=0.2)
				rivers.build(yellow, meander=0.2)


	##############################
	# 2. Standard River Generation
	##############################

	if river_opt == 0: # Custom rivers turned off
		rand_river_density = 0.5
	else: # Reduce random river density if custom rivers
		rand_river_density = 0.2
	riverGen = RiverGenerator(river_density=rand_river_density)
	riverGen.seedRivers()

	return None

# -----------------------------------------------------------------------------
# Starting plot
# -----------------------------------------------------------------------------

_START_PLOT_MAP = None

def minStartingDistanceModifier():
	return 15

def findStartingPlot(argsList):
	[playerID] = argsList
	global _START_PLOT_MAP

	if _START_PLOT_MAP is None:
		_START_PLOT_MAP = _assign_all_starting_plots()

	return _START_PLOT_MAP.get(playerID, -1)

def _is_real_coast(pPlot, min_water_size=5):
	"""
	Checks if a land plot is adjacent to a water body of at least min_water_size.
	This prevents players from being 'Coastal' next to a 1-tile desert pond.
	"""
	if pPlot.isWater(): return False
	map = CyMap()
	# Check all 8 directions (including diagonals) for ocean-sized water
	for dx in range(-1, 2):
		for dy in range(-1, 2):
			if dx == 0 and dy == 0: continue
			adj = map.plot(pPlot.getX() + dx, pPlot.getY() + dy)
			if adj and not adj.isNone():
				if adj.isWater():
					area = adj.area()
					if area and area.getNumTiles() >= min_water_size:
						return True
	return False

def _synced_shuffle(dice, lst):
	result = lst[:]
	for i in range(len(result) - 1, 0, -1):
		j = dice.get(i + 1, "Synced Shuffle")
		result[i], result[j] = result[j], result[i]
	return result

def _find_plot_in_rect(rect, region_name, assigned_coords, min_landmass=4, bPreferCoast=False, bPreferRiver=False):
	"""
	Return a plot index of a land tile inside the rectangle.
	rect format: (cX, cY, width, height)
	"""
	map = CyMap()
	dice = CyGlobalContext().getGame().getMapRand()
	iW, iH = map.getGridWidth(), map.getGridHeight()

	cX, cY, width, height = rect
	west_x = max(0, int(iW * (cX - (width / 2.0))))
	east_x = min(iW - 1, int(iW * (cX + (width / 2.0))))
	south_y = max(0, int(iH * (cY - (height / 2.0))))
	north_y = min(iH - 1, int(iH * (cY + (height / 2.0))))

	# Determine dynamic minimum distance based on map size
	min_dist = 6
	if map.getWorldSize() >= WorldSizeTypes.WORLDSIZE_LARGE:
		min_dist = 9

	# Step 1: Find all valid land plots in the rectangle
	base_eligible = []
	for x in range(west_x, east_x + 1):
		for y in range(south_y, north_y + 1):
			pPlot = map.plot(x, y)
			if pPlot and not pPlot.isWater() and not pPlot.isPeak():
				area = pPlot.area()
				if area and area.getNumTiles() >= min_landmass:
					base_eligible.append(pPlot)
	
	if not base_eligible: return -1

	# Step 2: Filter for Distance Safety (Best Effort)
	safe_eligible = []
	for pPlot in base_eligible:
		is_safe = True
		for (ax, ay) in assigned_coords:
			# plotDistance is the Civ4 standard for circular radius
			if plotDistance(pPlot.getX(), pPlot.getY(), ax, ay) < min_dist:
				is_safe = False
				break
		if is_safe:
			safe_eligible.append(pPlot)
			
	# If we found safe plots, they become our new candidates. 
	# If not, we use the original list (ignoring distance).
	if len(safe_eligible) > 0:
		candidates = safe_eligible
	else:
		candidates = base_eligible

	# Step 3: Apply Coast Preference
	if bPreferCoast:
		coastal_eligible = []
		for pPlot in candidates:
			if _is_real_coast(pPlot, 5):
				coastal_eligible.append(pPlot)
		if len(coastal_eligible) > 0:
			candidates = coastal_eligible

	# Step 4: Apply River Preference
	if bPreferRiver:
		river_eligible = []
		for pPlot in candidates:
			if pPlot.isRiver():
				river_eligible.append(pPlot)
		if len(river_eligible) > 0:
			candidates = river_eligible

	# Step 5: Final Selection
	idx = dice.get(len(candidates), "Historical start: %s" % region_name)
	target_plot = candidates[idx]
	return map.plotNum(target_plot.getX(), target_plot.getY())

def _fallback_start_placement(playerID, existing_coords):
	map = CyMap()
	gc = CyGlobalContext()
	dice = gc.getGame().getMapRand()
	player = gc.getPlayer(playerID)
	player.AI_updateFoundValues(True)

	COASTAL_START_BIAS = 1.35 

	# Gather the top 3 largest areas
	all_areas = []
	for i in range(map.getIndexAfterLastArea()):
		pArea = map.getArea(i)
		if pArea and not pArea.isNone() and not pArea.isWater():
			all_areas.append((pArea.getNumTiles(), pArea.getID()))
			
	# Sort largest to smallest, keep top 3
	all_areas.sort(key=lambda item: -item[0])
	valid_area_ids = []
	for i in range(min(3, len(all_areas))):
		valid_area_ids.append(all_areas[i][1])

	if not valid_area_ids:
		return -1 # Map has no land at all

	iW, iH = map.getGridWidth(), map.getGridHeight()
	
	# Start with a generous distance
	min_dist = 15
	if map.getWorldSize() >= WorldSizeTypes.WORLDSIZE_LARGE: 
		min_dist = 20

	candidates = []
	
	# Loop to progressively lower the distance requirement if the map is crowded
	while min_dist >= 0:
		
		# Iterate through the top 3 areas in order of size
		for target_area_id in valid_area_ids:
			for x in range(iW):
				for y in range(iH):
					pPlot = map.plot(x, y)
					
					# HARD CHECK: No Water, No Peaks, must be on Target Area
					if not pPlot or pPlot.isWater() or pPlot.isPeak(): continue
					if pPlot.getArea() != target_area_id: continue

					# Distance check using stepDistance (Chebyshev)
					is_too_close = False
					if min_dist > 0:
						for (ax, ay) in existing_coords:
							if stepDistance(x, y, ax, ay) < min_dist:
								is_too_close = True
								break
					if is_too_close: continue

					val = pPlot.getFoundValue(playerID)
					if val > 0:
						# Use the "Real Coast" check (adjacent to water body >= 10 tiles)
						# We use 10 here so they don't spawn on a tiny 2-tile lake
						if _is_real_coast(pPlot, 10):
							val *= COASTAL_START_BIAS
						candidates.append((val, map.plotNum(x, y)))
			
			# If we found at least one candidate in this area, we stop checking smaller areas
			if len(candidates) > 0:
				break
				
		# If we found at least one candidate across any area, break out of the distance loop
		if len(candidates) > 0:
			break
			
		# If no spots found on any of the top 3 continents, shrink the minimum distance and try again
		if min_dist == 0:
			break # Give up if even 0 distance fails
			
		min_dist -= 3 # Shrink requirement by 3 tiles and rescan
		if min_dist < 0:
			min_dist = 0

	# Absolute emergency fallback if a civilization literally values NO land plot
	if not candidates:
		for x in range(iW):
			for y in range(iH):
				pPlot = map.plot(x, y)
				if pPlot and not pPlot.isWater() and not pPlot.isPeak() and pPlot.getArea() in valid_area_ids:
					candidates.append((10, map.plotNum(x, y)))
		
		if not candidates:
			# If still nothing, let Civ4 handle it
			return CvMapGeneratorUtil.findStartingPlot(playerID)

	# Sort by highest found value
	candidates.sort(key=lambda item: -item[0])
	num_best_choices = min(5, len(candidates))
	return candidates[dice.get(num_best_choices, "Fallback Start Choice")][1]

def _add_spawn_signs(spawn_dict):
	"""Adds map signs to the center of each historical spawn region."""
	m = CyMap()
	engine = CyEngine()
	iW = m.getGridWidth()
	iH = m.getGridHeight()
	
	# In Python 2.4, iterating over keys is the safest method
	for name in spawn_dict.keys():
		data = spawn_dict[name]
		cx = data[0]
		cy = data[1]
		
		# Convert fractional center to plot coordinates
		iX = int(iW * cx)
		iY = int(iH * cy)
		
		pPlot = m.plot(iX, iY)
		if pPlot:
			if not pPlot.isNone():
				# -1 makes the sign visible to all players
				# engine.addSign(pPlot, -1, "Spawn: " + str(name))
				engine.addSign(pPlot, -1, str(name))

# Run Starting Plot Assignments
def _assign_all_starting_plots():
	print "PY: Assigning all starting plots..."
	map = CyMap()
	gc = CyGlobalContext()
	dice = gc.getGame().getMapRand()
	# Force a recalculation of areas to ensure 'isWater' and 'area size' are accurate
	map.recalculateAreas()
	
	start_option = map.getCustomMapOption(5)

	final_assignments = {} 
	assigned_coords = []   
	used_regions = set()
	unassigned_players = []

	# Format: (cX, cY, width, height, bPreferCoast, bPreferRiver)
	SPAWN_REGIONS = {
		"Tasmania": (0.628, 0.072, 0.102, 0.135, True, False),
		"Sydney": (0.721, 0.316, 0.102, 0.166, True, False),
		"Brisbane": (0.74, 0.529, 0.082, 0.195, False, False),
		"Adelaide": (0.49, 0.307, 0.096, 0.143, False, False),
		"Perth": (0.171, 0.327, 0.106, 0.243, False, False),
		"Darwin": (0.424, 0.871, 0.146, 0.114, False, False),
		"NZ": (0.909, 0.208, 0.176, 0.423, False, False),
		"NewGuinea": (0.643, 0.973, 0.22, 0.071, False, False),
		"East_Indies": (0.166, 0.939, 0.332, 0.123, False, False),
		"Melbourne": (0.596, 0.221, 0.102, 0.111, False, False),
	}

	primary_regions = ["Sydney", "Brisbane", "Adelaide", "Perth", "Darwin", "NZ", "Melbourne"]
	secondary_regions = ["Tasmania", "NewGuinea", "East_Indies"]
	tertiary_regions = []

	civ_mapping = {
		"CIVILIZATION_ENGLAND":      "Melbourne",
		"CIVILIZATION_CELT":      "Sydney",
		"CIVILIZATION_NETHERLANDS":      "Tasmania",
	}

	all_players = []
	for i in range(gc.getMAX_CIV_PLAYERS()):
		player = gc.getPlayer(i)
		if player.isEverAlive():
			all_players.append(i)
	
	# --- PHASE 1: Fixed Assignments ---
	if start_option == 1:
		# Call this here to place Debug signs on the map
		_add_spawn_signs(SPAWN_REGIONS)
		
		for playerID in all_players:
			civ_str = gc.getCivilizationInfo(gc.getPlayer(playerID).getCivilizationType()).getType()
			region_name = civ_mapping.get(civ_str)
			
			if region_name and region_name not in used_regions:
				data = SPAWN_REGIONS[region_name]
				# Center-based rect: (cX, cY, w, h)
				rect = (data[0], data[1], data[2], data[3])
				plot_index = _find_plot_in_rect(rect, "Fixed: " + region_name, assigned_coords, 4, data[4], data[5])
				
				if plot_index != -1:
					final_assignments[playerID] = plot_index
					print "MAP DEBUG: Fixed Start - %s assigned to %s" % (civ_str, region_name)
					p = map.plotByIndex(plot_index)
					assigned_coords.append((p.getX(), p.getY()))
					used_regions.add(region_name)
					continue 
			unassigned_players.append(playerID)
	else:
		unassigned_players = all_players

	# --- PHASE 2: Prioritized Regional Shuffle ---
	if start_option == 1 and unassigned_players:
		print "MAP DEBUG: Attempting prioritized historical region assignment"
		unassigned_players = _synced_shuffle(dice, unassigned_players)
		
		p_avail = []
		for r in primary_regions:
			if r not in used_regions: p_avail.append(r)
		s_avail = []
		for r in secondary_regions:
			if r not in used_regions: s_avail.append(r)
			
		available_regions = _synced_shuffle(dice, p_avail) + _synced_shuffle(dice, s_avail)
		
		still_unassigned = []
		for playerID in unassigned_players:
			civ_str = gc.getCivilizationInfo(gc.getPlayer(playerID).getCivilizationType()).getType()
			if available_regions:
				fallback_region = available_regions.pop(0)
				data = SPAWN_REGIONS[fallback_region]
				rect = (data[0], data[1], data[2], data[3])
				plot_index = _find_plot_in_rect(rect, "Region-Shuffle: " + fallback_region, assigned_coords, 4, data[4], data[5])
				if plot_index != -1:
					final_assignments[playerID] = plot_index
					print "MAP DEBUG: Region-Shuffle - %s assigned to %s" % (civ_str, fallback_region)
					p = map.plotByIndex(plot_index)
					assigned_coords.append((p.getX(), p.getY()))
				else:
					still_unassigned.append(playerID)
			else:
				still_unassigned.append(playerID)
		unassigned_players = still_unassigned

	# --- PHASE 3: Generic Fallback ---
	if unassigned_players:
		for playerID in unassigned_players:
			plot_index = _fallback_start_placement(playerID, assigned_coords)
			if plot_index != -1:
				final_assignments[playerID] = plot_index
				civ_str = gc.getCivilizationInfo(gc.getPlayer(playerID).getCivilizationType()).getType()
				p = map.plotByIndex(plot_index)
				print "MAP DEBUG: Generic Fallback - %s assigned to (%d, %d)" % (civ_str, p.getX(), p.getY())
				assigned_coords.append((p.getX(), p.getY()))
				
	return final_assignments


# -----------------------------------------------------------------------------
# Normalization overrides
# -----------------------------------------------------------------------------
def normalizeAddRiver():
	return None

def normalizeRemovePeaks():
	"""
	Remove peaks only from the 1-tile radius of each player's starting plot.
	This overrides the default peak removal that could strip too many peaks.
	"""
	map = CyMap()
	gc = CyGlobalContext()
	iW = map.getGridWidth()
	iH = map.getGridHeight()

	# Collect all starting plots
	starts = []
	for i in range(gc.getMAX_CIV_PLAYERS()):
		player = gc.getPlayer(i)
		if player.isEverAlive():
			start_plot = player.getStartingPlot()
			if start_plot:
				starts.append((start_plot.getX(), start_plot.getY()))

	# For each start, look at plots within Chebyshev distance <= 1 (3x3 area)
	for sx, sy in starts:
		for dx in range(-1, 2):
			for dy in range(-1, 2):
				x = sx + dx
				y = sy + dy
				if 0 <= x < iW and 0 <= y < iH:
					pPlot = map.plot(x, y)
					if pPlot.getPlotType() == PlotTypes.PLOT_PEAK:
						# Convert to hills
						pPlot.setPlotType(PlotTypes.PLOT_HILLS, True, True)

def normalizeAddGoodTerrain():
	return None

def normalizeRemoveBadTerrain():
	return None

def normalizeRemoveBadFeatures():
	return None

def normalizeAddFoodBonuses():
	return None

def normalizeAddExtras():
	#CyPythonMgr().allowDefaultImpl() # disable default nomalizer
	addCustomResources() # custom Resource Generator

# -----------------------------------------------------------------------------
# Custom resource addition – Main entry point for all  resource handling
# -----------------------------------------------------------------------------

class ResourceManager:
	"""Manages custom resource placement for the Mediterranean map script."""
	def __init__(self, map, gc, dice, iW, iH):
		self.map = map
		self.gc = gc
		self.dice = dice
		self.iW = iW
		self.iH = iH
		self._cache = {}   
		
		self.world_size = self.map.getWorldSize()
		self.size_multiplier = {
			WorldSizeTypes.WORLDSIZE_DUEL:     0.5,
			WorldSizeTypes.WORLDSIZE_TINY:     0.5,
			WorldSizeTypes.WORLDSIZE_SMALL:    1,
			WorldSizeTypes.WORLDSIZE_STANDARD: 1,
			WorldSizeTypes.WORLDSIZE_LARGE:    1.34,
			WorldSizeTypes.WORLDSIZE_HUGE:     1.5,
		}

	def _bonus_id(self, name):
		if name in self._cache: return self._cache[name]
		bid = self.gc.getInfoTypeForString(name)
		self._cache[name] = bid
		return bid

	def _is_bonus_appropriate_for_plot(self, bonus_id, pPlot):
		"""
		Checks if the bonus is physically compatible with the plot's 
		terrain, topography, and feature, ignoring proximity and latitude.
		"""
		info = self.gc.getBonusInfo(bonus_id)
		
		# 1. Check Topography (Hills vs Flat)
		if pPlot.isHills():
			if not info.isHills(): return False
		else:
			if not info.isFlatlands(): return False
			
		# 2. Check Terrain
		if not info.isTerrain(pPlot.getTerrainType()):
			return False
			
		# 3. Check Feature
		iFeature = pPlot.getFeatureType()
		if iFeature != -1:
			if not info.isFeature(iFeature):
				# Special case: If it's a feature we are willing to clear (Forest/Jungle)
				# and the bonus is valid on the underlying terrain, we count it as 'appropriate'
				# because our placement logic handles the clearing.
				iFloodplains = self.gc.getInfoTypeForString("FEATURE_FLOOD_PLAINS")
				if iFeature == iFloodplains: return False # Floodplains usually strictly defined in XML
				
				# If the bonus can't exist with the feature AND we aren't allowed to clear it, return False
				# But for your script, we usually assume we can clear Forest/Jungle for a Tier 1 match.
				if not info.isTerrain(pPlot.getTerrainType()):
					return False

		return True

	def _is_bonus_appropriate_plot_type(self, bonus_id, pPlot):
		"""
		Checks only whether the bonus can use this plot's topography.
		Used as the fallback tier for region-specific placement.
		"""
		if pPlot.isWater(): return False
		if pPlot.getPlotType() == PlotTypes.PLOT_PEAK: return False

		info = self.gc.getBonusInfo(bonus_id)
		if pPlot.isHills():
			if not info.isHills(): return False
		else:
			if not info.isFlatlands(): return False

		return True
	
	def place_bonus_in_BFC(self, bonus_list, count=1, check_existence=False):
		"""
		Tiered placement logic for LAND starting resources.
		1. Natural Fit: Shuffles bonuses and finds a tile that matches terrain requirements.
		2. Emergency: Terraforms a foodless tile to Plains Flat and picks a valid bonus.
		"""
		ids = []
		for b in bonus_list:
			ids.append(self._bonus_id(b))

		iPlains = self.gc.getInfoTypeForString("TERRAIN_PLAINS")
		iDesert = self.gc.getInfoTypeForString("TERRAIN_DESERT")
		iFloodplains = self.gc.getInfoTypeForString("FEATURE_FLOOD_PLAINS")

		players = []
		for i in range(self.gc.getMAX_CIV_PLAYERS()):
			player = self.gc.getPlayer(i)
			if player.isEverAlive():
				pStart = player.getStartingPlot()
				if pStart and not pStart.isNone():
					players.append((player.getID(), pStart.getX(), pStart.getY()))

		for (pid, sx, sy) in players:
			# 1. Define the Big Fat Cross (21 tiles)
			bfc_offsets = []
			for dx in range(-2, 3):
				for dy in range(-2, 3):
					if dx == 0 and dy == 0: continue 
					if abs(dx) == 2 and abs(dy) == 2: continue 
					bfc_offsets.append((dx, dy))

			# 2. Count existing resources from the list in the BFC (Exclude the center tile)
			existing_count = 0
			if check_existence:
				for dx, dy in bfc_offsets:
					nx, ny = sx + dx, sy + dy
					if 0 <= nx < self.iW and 0 <= ny < self.iH:
						pPlot = self.map.plot(nx, ny)
						if pPlot.isStartingPlot(): continue
						if pPlot.getBonusType(-1) in ids:
							existing_count += 1
			
			needed = count - existing_count
			
			# 3. Placement Loop: Run for every bonus still required
			for i in range(needed):
				# Shuffle the full list for every individual placement attempt
				shuffled_ids = _synced_shuffle(self.dice, ids[:])
				placed_successfully = False

				# --- TIER 1: NATURAL FIT ---
				# We iterate through the shuffled bonuses. If Bonus A doesn't fit 
				# anywhere in the BFC, we move to Bonus B.
				for chosen_id in shuffled_ids:
					tier1_plots = []
					for dx, dy in bfc_offsets:
						nx, ny = sx + dx, sy + dy
						if 0 <= nx < self.iW and 0 <= ny < self.iH:
							pPlot = self.map.plot(nx, ny)
							
							# Filter: No starts, no existing bonuses, NO WATER, NO PEAKS
							if pPlot.isStartingPlot() or pPlot.getBonusType(-1) != -1: continue
							if pPlot.isWater() or pPlot.isPeak(): continue

							# Use our manual check to see if the bonus fits this tile's terrain
							if self._is_bonus_appropriate_for_plot(chosen_id, pPlot):
								tier1_plots.append(pPlot)

					if len(tier1_plots) > 0:
						target_plot = tier1_plots[self.dice.get(len(tier1_plots), "T1 Plot")]
						
						# Handle feature clearing (Forest/Jungle), but keep Floodplains
						current_feature = target_plot.getFeatureType()
						if current_feature != -1 and current_feature != iFloodplains:
							# Clear feature if the bonus can't naturally sit on it (e.g. Wheat in Forest)
							if not target_plot.canHaveBonus(chosen_id, True):
								target_plot.setFeatureType(FeatureTypes.NO_FEATURE, -1)

						target_plot.setBonusType(chosen_id)
						placed_successfully = True
						break # Successfully placed a Tier 1 bonus, move to next 'needed'

				# --- TIER 2: EMERGENCY TERRAFORM ---
				# Runs only if NO bonus in the list fits naturally anywhere in the BFC
				if not placed_successfully:
					emergency_plots = []
					for dx, dy in bfc_offsets:
						nx, ny = sx + dx, sy + dy
						if 0 <= nx < self.iW and 0 <= ny < self.iH:
							pPlot = self.map.plot(nx, ny)
							if pPlot.isStartingPlot() or pPlot.getBonusType(-1) != -1: continue
							if pPlot.isWater() or pPlot.isPeak(): continue

							# Target: Desert, Hills, or Floodplains (all considered 'foodless' candidates)
							# calculateNatureYield(Yield, Team, bIgnoreFeature)
							if pPlot.calculateNatureYield(YieldTypes.YIELD_FOOD, TeamTypes.NO_TEAM, False) == 0:
								emergency_plots.append(pPlot)
							elif pPlot.getFeatureType() == iFloodplains:
								emergency_plots.append(pPlot)

					if len(emergency_plots) > 0:
						target_plot = emergency_plots[self.dice.get(len(emergency_plots), "Emergency Plot")]
						
						# 1. Terraform to Plains Flatland
						target_plot.setPlotType(PlotTypes.PLOT_LAND, True, True)
						target_plot.setTerrainType(iPlains, True, True)
						target_plot.setFeatureType(FeatureTypes.NO_FEATURE, -1)

						# 2. Re-filter the shuffled list for the new Plains Flatland tile
						for b_id in shuffled_ids:
							if self._is_bonus_appropriate_for_plot(b_id, target_plot):
								target_plot.setBonusType(b_id)
								placed_successfully = True
								break
						
						# 3. Brute Force: If for some reason nothing fit the manual check, force the first one
						if not placed_successfully:
							target_plot.setBonusType(shuffled_ids[0])

	def place_bonus_in_radius(self, bonus_list, radius=5):
		"""
		Generic function to ensure a resource type exists within a radius.
		Uses plotDistance to ensure diagonal resources are correctly scanned.
		"""
		ids = []
		for b in bonus_list:
			ids.append(self._bonus_id(b))

		players = []
		for i in range(self.gc.getMAX_CIV_PLAYERS()):
			player = self.gc.getPlayer(i)
			if player.isEverAlive():
				pStart = player.getStartingPlot()
				if pStart and not pStart.isNone():
					players.append((player.getID(), pStart.getX(), pStart.getY()))

		for (pid, sx, sy) in players:
			# Step 1: Scan for existing bonuses from the list
			has_bonus = False
			found_x, found_y = -1, -1
			
			# Nested loop creates a square, plotDistance trims it to a circle
			for dx in range(-radius, radius + 1):
				for dy in range(-radius, radius + 1):
					nx, ny = sx + dx, sy + dy
					
					# Boundary check
					if 0 <= nx < self.iW and 0 <= ny < self.iH:
						# plotDistance is the engine's standard for circular radii
						if plotDistance(sx, sy, nx, ny) <= radius:
							pPlot = self.map.plot(nx, ny)
							# Use TeamTypes.NO_TEAM to see all placed bonuses
							if pPlot.getBonusType(TeamTypes.NO_TEAM) in ids:
								has_bonus = True
								found_x, found_y = nx, ny
								break
				if has_bonus: break
			
			if has_bonus:
				# DEBUG: Place a sign on the EXISTING resource that triggered the skip
				# This helps you verify that the Horse 3 tiles away was actually detected.
				# CyEngine().addSign(self.map.plot(found_x, found_y), -1, "DEBUG: Found existing for P%d" % pid)
				print "MAP DEBUG: Player %d skipped. Found existing bonus at (%d, %d)" % (pid, found_x, found_y)
				continue

			# Step 2: Placement (Same logic as before, but using plotDistance for consistency)
			shuffled_ids = _synced_shuffle(self.dice, ids[:])
			placed_successfully = False
			target_plot = None
			final_id = -1

			# TIER 1: Natural Fit
			for chosen_id in shuffled_ids:
				tier1_plots = []
				for dx in range(-radius, radius + 1):
					for dy in range(-radius, radius + 1):
						nx, ny = sx + dx, sy + dy
						if 0 <= nx < self.iW and 0 <= ny < self.iH:
							if plotDistance(sx, sy, nx, ny) <= radius:
								pPlot = self.map.plot(nx, ny)
								if pPlot.isStartingPlot() or pPlot.getBonusType(-1) != -1: continue
								if pPlot.isWater() or pPlot.isPeak(): continue

								if self._is_bonus_appropriate_for_plot(chosen_id, pPlot):
									tier1_plots.append(pPlot)

				if len(tier1_plots) > 0:
					target_plot = tier1_plots[self.dice.get(len(tier1_plots), "Radius T1")]
					final_id = chosen_id
					placed_successfully = True
					break 

			# TIER 2: Emergency (Any Land)
			if not placed_successfully:
				emergency_plots = []
				for dx in range(-radius, radius + 1):
					for dy in range(-radius, radius + 1):
						nx, ny = sx + dx, sy + dy
						if 0 <= nx < self.iW and 0 <= ny < self.iH:
							if plotDistance(sx, sy, nx, ny) <= radius:
								pPlot = self.map.plot(nx, ny)
								if not pPlot.isWater() and not pPlot.isPeak() and not pPlot.isStartingPlot():
									if pPlot.getBonusType(-1) == -1:
										emergency_plots.append(pPlot)

				if len(emergency_plots) > 0:
					target_plot = emergency_plots[self.dice.get(len(emergency_plots), "Radius Emergency")]
					final_id = shuffled_ids[0]
					placed_successfully = True

			if placed_successfully and target_plot:
				target_plot.setBonusType(final_id)
				
				# Visual Marker for newly added resources
				bonus_name = self.gc.getBonusInfo(final_id).getType()
				# CyEngine().addSign(target_plot, -1, "DEBUG: Added " + bonus_name)
				print "MAP DEBUG: Placed %s for Player %d at (%d, %d)" % (bonus_name, pid, target_plot.getX(), target_plot.getY())


	def swap_resources(self, swap_rules, clear_feature=False):
		"""
		Swaps resources globally. Now explicitly skips starting plots to 
		prevent accidental changes to the capital's immediate tile.
		"""
		for rule in swap_rules:
			old_name = rule[0]
			new_name = rule[1]
			if len(rule) > 2:
				min_y_fraction = rule[2]
			else:
				min_y_fraction = 0.0
			
			old_id = self._bonus_id(old_name)
			y_thresh = int(self.iH * min_y_fraction)

			for i in range(self.map.numPlots()):
				pPlot = self.map.plotByIndex(i)
				# EXCLUDE starting plots from global swaps
				if pPlot.isStartingPlot(): continue
				
				if pPlot.getY() >= y_thresh and pPlot.getBonusType(-1) == old_id:
					if new_name:
						pPlot.setBonusType(self._bonus_id(new_name))
					else:
						pPlot.setBonusType(-1)
					
					if clear_feature:
						pPlot.setFeatureType(FeatureTypes.NO_FEATURE, -1)

	def _is_feature_allowed_for_bonus(self, bonus_id, feature_id):
		if feature_id == -1:
			return True

		bonusInfo = self.gc.getBonusInfo(bonus_id)
		iFeatureCount = self.gc.getNumFeatureInfos()
		for i in range(iFeatureCount):
			if i == feature_id:
				if bonusInfo.isFeature(i):
					return True
				return False

		return False

	def add_region_specific(self, region_specs, bChangePlains=False):
		"""
		Place bonuses in specified regions using center-based coordinates. 
		region["rect"] format: (cX, cY, width, height)
		region["bonuses"] entry format: (bonus_type, count, bChangePlains)
		"""
		multiplier = self.size_multiplier[self.world_size]
		iPlains = self.gc.getInfoTypeForString("TERRAIN_PLAINS")
		
		for region in region_specs:
			# Unpack center-based coordinates
			cX, cY, width, height = region["rect"]
			
			# Calculate pixel-grid boundaries from center
			west_x = int(self.iW * (cX - (width / 2.0)))
			east_x = int(self.iW * (cX + (width / 2.0)))
			south_y = int(self.iH * (cY - (height / 2.0)))
			north_y = int(self.iH * (cY + (height / 2.0)))

			# Clamp to map edges
			iWest = max(0, west_x)
			iEast = min(self.iW - 1, east_x)
			iSouth = max(0, south_y)
			iNorth = min(self.iH - 1, north_y)

			for bonus_entry in region["bonuses"]:
				scaled_count = int(bonus_entry[1] * multiplier)
				if scaled_count == 0: 
					continue
					
				bonus_id = self._bonus_id(bonus_entry[0])
				if len(bonus_entry) > 2:
					bBonusChangePlains = bonus_entry[2]
				else:
					bBonusChangePlains = False
				
				eligible = []
				plot_type_fallback = []
				
				# Scan the calculated rectangle
				for x in range(iWest, iEast + 1):
					for y in range(iSouth, iNorth + 1):
						pPlot = self.map.plot(x, y)
						
						# EXCLUDE starting plots from region-specific placement
						if pPlot.isStartingPlot(): 
							continue
						
						if pPlot.getBonusType(-1) == -1:
							if pPlot.canHaveBonus(bonus_id, True):
								eligible.append((x, y))
							elif self._is_bonus_appropriate_plot_type(bonus_id, pPlot):
								plot_type_fallback.append((x, y))

				# Placement Loop
				placed = 0
				for _ in range(scaled_count):
					choice = None
					bChangeTerrain = False
					if eligible:
						choice = eligible.pop(self.dice.get(len(eligible), "Region Bonus"))
					elif plot_type_fallback:
						choice = plot_type_fallback.pop(self.dice.get(len(plot_type_fallback), "Fallback Bonus"))
						if bBonusChangePlains:
							bChangeTerrain = True
					
					if choice:
						p = self.map.plot(choice[0], choice[1])
						if bChangeTerrain:
							p.setTerrainType(iPlains, True, True)
							iFeature = p.getFeatureType()
							if not self._is_feature_allowed_for_bonus(bonus_id, iFeature):
								p.setFeatureType(FeatureTypes.NO_FEATURE, -1)
						p.setBonusType(bonus_id)
						placed += 1

def addCustomResources():
	m = CyMap()
	gc = CyGlobalContext()
	dice = gc.getGame().getMapRand()
	iW = m.getGridWidth()
	iH = m.getGridHeight()
	rm = ResourceManager(m, gc, dice, iW, iH)
	
	# Custom Options
	food_count = m.getCustomMapOption(4) # 0, 1, or 2
	historical_on = (m.getCustomMapOption(3) == 0)

	if historical_on: # Region-specific resources
		region_specs = [
			{
				"name": "NSW_gold",
				"rect": (0.626, 0.253, 0.12, 0.16),
				"bonuses": [
					("BONUS_GOLD", 1, False),
					("BONUS_SILVER", 1, False),
				]
			},
			{
				"name": "WA",
				"rect": (0.183, 0.443, 0.164, 0.378),
				"bonuses": [
					("BONUS_GOLD", 2, False),
					("BONUS_DEER", 2, True),
				]
			},
			{
				"name": "SA_gold",
				"rect": (0.496, 0.363, 0.108, 0.132),
				"bonuses": [
					("BONUS_GOLD", 1, False),
					("BONUS_SILVER", 1, False),
				]
			},
			{
				"name": "NT_Silver",
				"rect": (0.474, 0.691, 0.116, 0.138),
				"bonuses": [
					("BONUS_SILVER", 2, False),
				]
			},
			{
				"name": "QLD_Coast",
				"rect": (0.678, 0.657, 0.102, 0.203),
				"bonuses": [
					("BONUS_SUGAR", 2, False),
					("BONUS_GOLD", 1, False),
				]
			},
			{
				"name": "WA_Diamonds",
				"rect": (0.309, 0.796, 0.1, 0.12),
				"bonuses": [
					("BONUS_GEMS", 2, False),
					("BONUS_IRON", 1, False),
				]
			},
			{
				"name": "NT_Aluminum",
				"rect": (0.514, 0.869, 0.276, 0.1),
				"bonuses": [
					("BONUS_ALUMINUM", 2, False),
				]
			},
			{
				"name": "Rottsnest_Quokka",
				"rect": (0.112, 0.269, 0.078, 0.086),
				"bonuses": [
					("BONUS_FUR", 1, False),
				]
			},
			{
				"name": "Bonus_Tasmania",
				"rect": (0.629, 0.06, 0.132, 0.149),
				"bonuses": [
					("BONUS_CLAM", 1, False),
					("BONUS_DEER", 1, False),
					("BONUS_COPPER", 1, False),
					("BONUS_FUR", 1, False),
				]
			},
			{
				"name": "Kangaroos",
				"rect": (0.617, 0.461, 0.158, 0.232),
				"bonuses": [
					("BONUS_DEER", 2, True),
				]
			},
			{
				"name": "EastIndies",
				"rect": (0.158, 0.956, 0.304, 0.1),
				"bonuses": [
					("BONUS_SPICES", 1, False),
				]
			},
			{
				"name": "Wallabies",
				"rect": (0.719, 0.42, 0.152, 0.354),
				"bonuses": [
					("BONUS_FUR", 2, False),
				]
			},
			{
				"name": "NZ_Resources",
				"rect": (0.929, 0.228, 0.176, 0.423),
				"bonuses": [
					("BONUS_SHEEP", 1, False),
					("BONUS_FUR", 1, False),
				]
			},
		]
		rm.add_region_specific(region_specs, bChangePlains=True)

	if historical_on:  # Map-wide Swaps
		swap_rules =[]
		swap_rules.append(("BONUS_CORN", "BONUS_WHEAT")) # Swap corn for wheat

	rm.swap_resources(swap_rules)

	# 3. Strategic resources
	strategic_list = ["BONUS_COPPER", "BONUS_IRON", "BONUS_HORSE"]
	rm.place_bonus_in_radius(strategic_list, radius=5)

	# 4. Food resources
	food_list = ["BONUS_WHEAT", "BONUS_RICE", "BONUS_CORN", "BONUS_COW", "BONUS_SHEEP", "BONUS_PIG", "BONUS_DEER"]
	rm.place_bonus_in_BFC(food_list, count=food_count, check_existence=True)
