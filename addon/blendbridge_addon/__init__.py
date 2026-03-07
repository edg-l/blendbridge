import bpy
from bpy.props import IntProperty, BoolProperty

from . import server


class BlendBridgePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    port: IntProperty(
        name="Port",
        description="HTTP server port",
        default=8400,
        min=1024,
        max=65535,
    )

    auto_start: BoolProperty(
        name="Auto-start Server",
        description="Start HTTP server when addon is enabled",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "port")
        layout.prop(self, "auto_start")

        if server.is_running():
            layout.label(text=f"Server running on port {self.port}", icon="CHECKMARK")
            layout.operator("blendbridge.stop_server")
        else:
            layout.label(text="Server not running", icon="ERROR")
            layout.operator("blendbridge.start_server")


class BLENDBRIDGE_OT_start_server(bpy.types.Operator):
    bl_idname = "blendbridge.start_server"
    bl_label = "Start Server"
    bl_description = "Start the BlendBridge HTTP server"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        server.start(prefs.port)
        self.report({"INFO"}, f"BlendBridge server started on port {prefs.port}")
        return {"FINISHED"}


class BLENDBRIDGE_OT_stop_server(bpy.types.Operator):
    bl_idname = "blendbridge.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the BlendBridge HTTP server"

    def execute(self, context):
        server.stop()
        self.report({"INFO"}, "BlendBridge server stopped")
        return {"FINISHED"}


classes = (
    BlendBridgePreferences,
    BLENDBRIDGE_OT_start_server,
    BLENDBRIDGE_OT_stop_server,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    prefs = bpy.context.preferences.addons.get(__package__)
    if prefs and prefs.preferences.auto_start:
        server.start(prefs.preferences.port)


def unregister():
    server.stop()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
