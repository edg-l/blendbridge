import bpy
from bpy.props import IntProperty, BoolProperty

from . import server


class BlenderAgentPreferences(bpy.types.AddonPreferences):
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
            layout.operator("blenderagent.stop_server")
        else:
            layout.label(text="Server not running", icon="ERROR")
            layout.operator("blenderagent.start_server")


class BLENDERAGENT_OT_start_server(bpy.types.Operator):
    bl_idname = "blenderagent.start_server"
    bl_label = "Start Server"
    bl_description = "Start the BlenderAgent HTTP server"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        server.start(prefs.port)
        self.report({"INFO"}, f"BlenderAgent server started on port {prefs.port}")
        return {"FINISHED"}


class BLENDERAGENT_OT_stop_server(bpy.types.Operator):
    bl_idname = "blenderagent.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the BlenderAgent HTTP server"

    def execute(self, context):
        server.stop()
        self.report({"INFO"}, "BlenderAgent server stopped")
        return {"FINISHED"}


classes = (
    BlenderAgentPreferences,
    BLENDERAGENT_OT_start_server,
    BLENDERAGENT_OT_stop_server,
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
