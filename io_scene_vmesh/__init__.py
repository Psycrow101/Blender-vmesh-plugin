bl_info = {
    "name": "Valve vmesh_c importer",
    "author": "Perry & Ricochet",
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import compiled vmesh animations.",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}


import bpy
from bpy.props import *
from bpy_extras.io_utils import (
    ImportHelper,
    orientation_helper,
    axis_conversion,
)


if "bpy" in locals():
    import importlib

    if "vmesh_import" in locals():
        importlib.reload(vmesh_import)

@orientation_helper(axis_forward='-X', axis_up='Z')
class IMPORT_OT_vmesh(bpy.types.Operator, ImportHelper):
    #Import a vmesh file
    bl_idname = "import_scene.vmesh_c"
    bl_label = "Import vmesh"
    bl_options = {'PRESET', 'UNDO'}

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    filename_ext = ".vmesh_c"
    filter_glob: StringProperty(default="*.vmesh_c", options={'HIDDEN'})

    add_hitboxes: BoolProperty(
        name="Add hitboxes",
        description="Add empty entities to indicate hitboxes",
        default=True,
    )

    def execute(self, context):
        from . import vmesh_import

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))
        keywords["global_matrix"] = axis_conversion(from_forward=self.axis_forward,
                                                    from_up=self.axis_up,
                                                    ).to_4x4()

        vmesh_import.import_file(context, **keywords)
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(IMPORT_OT_vmesh.bl_idname, text="Compiled vmesh (.vmesh_c)")


classes = (
    IMPORT_OT_vmesh,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)

    
def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()