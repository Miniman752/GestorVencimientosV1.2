try:
    from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker
    print("ScalingTracker found.")
    print("Attributes:", dir(ScalingTracker))
    
    # Check if there is a stop mechanism
    if hasattr(ScalingTracker, 'deactivate_scaling_tracker'):
         print("Found deactivate_scaling_tracker")
    if hasattr(ScalingTracker, 'stop'):
         print("Found stop")
    
except ImportError:
    print("Could not import ScalingTracker directly.")
    import customtkinter
    print("CTK Dirt:", dir(customtkinter))
