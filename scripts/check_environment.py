import importlib,json,sys
results={}
for name in ('pptx','PIL'):
    try:
        importlib.import_module(name)
        results[name]={'available':True}
    except Exception as error:
        results[name]={'available':False,'error':str(error)}
print(json.dumps({'python':sys.executable,'dependencies':results},ensure_ascii=False))
sys.exit(0 if all(item['available'] for item in results.values()) else 1)
