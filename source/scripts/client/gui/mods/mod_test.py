import items.vehicles
import nations

data = {camouflage['name']: camoID for camoID, camouflage in items.vehicles.g_cache.customization(0)['camouflages'].iteritems()}
for nationID in xrange(1, len(nations.NAMES)):
    camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
    camoNames = [camouflage['name'] for camouflage in camouflages.itervalues()]
    for camoName, camoID in data.items():
        if camoName not in camoNames:
            del data[camoName]

print data
for nationID in xrange(len(nations.NAMES)):
    camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
    camoData = {camouflage['name']: camoID for camoID, camouflage in camouflages.iteritems()}
    print {camoName: camoData[camoName] for camoName in data}
