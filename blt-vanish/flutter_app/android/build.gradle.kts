allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}

subprojects {
    val configureTasks = {
        // Force all Android subprojects to use NDK version 30.0.15729638
        extensions.findByName("android")?.let { android ->
            try {
                android.javaClass.getMethod("setNdkVersion", String::class.java).invoke(android, "30.0.15729638")
            } catch (e: Exception) {
                try {
                    android.javaClass.getMethod("ndkVersion", String::class.java).invoke(android, "30.0.15729638")
                } catch (ex: Exception) {
                    try {
                        android.javaClass.getMethod("setNdkVersion", Any::class.java).invoke(android, "30.0.15729638")
                    } catch (ex2: Exception) {}
                }
            }
        }

        tasks.findByName("stripReleaseDebugSymbols")?.let { stripTask ->
            if (stripTask.hasProperty("inputDir")) {
                val createDirTask = tasks.register("createStripReleaseOutputDir") {
                    doLast {
                        val inputDirObj = stripTask.property("inputDir")
                        if (inputDirObj != null) {
                            val dir = project.file(inputDirObj)
                            if (!dir.exists()) {
                                dir.mkdirs()
                            }
                        }
                    }
                }
                stripTask.dependsOn(createDirTask)
            }
        }
        tasks.findByName("stripDebugDebugSymbols")?.let { stripTask ->
            if (stripTask.hasProperty("inputDir")) {
                val createDirTask = tasks.register("createStripDebugOutputDir") {
                    doLast {
                        val inputDirObj = stripTask.property("inputDir")
                        if (inputDirObj != null) {
                            val dir = project.file(inputDirObj)
                            if (!dir.exists()) {
                                dir.mkdirs()
                            }
                        }
                    }
                }
                stripTask.dependsOn(createDirTask)
            }
        }
    }

    if (state.executed) {
        configureTasks()
    } else {
        afterEvaluate {
            configureTasks()
        }
    }
}


