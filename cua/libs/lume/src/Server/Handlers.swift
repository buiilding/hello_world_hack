import ArgumentParser
import Foundation
import Virtualization

@MainActor
extension Server {
    // MARK: - VM Management Handlers

    func handleListVMs(storage: String? = nil) async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            let vms = try vmController.list(storage: storage)
            return try .json(vms)
        } catch {
            print(
                "ERROR: Failed to list VMs: \(error.localizedDescription), storage=\(String(describing: storage))"
            )
            return .badRequest(message: error.localizedDescription)
        }
    }

    func handleGetVM(name: String, storage: String? = nil) async throws -> HTTPResponse {
        print("Getting VM details: name=\(name), storage=\(String(describing: storage))")

        do {
            let vmController = LumeController()
            print("Created VM controller, attempting to get VM")
            let vm = try vmController.get(name: name, storage: storage)
            print("Successfully retrieved VM")

            // Check for nil values that might cause crashes
            if vm.vmDirContext.config.macAddress == nil {
                print("ERROR: VM has nil macAddress")
                return .badRequest(message: "VM configuration is invalid (nil macAddress)")
            }
            print("MacAddress check passed")

            // Log that we're about to access details
            print("Preparing VM details response")

            // Print the full details object for debugging
            let details = vm.details
            print("VM DETAILS: \(details)")
            print("  name: \(details.name)")
            print("  os: \(details.os)")
            print("  cpuCount: \(details.cpuCount)")
            print("  memorySize: \(details.memorySize)")
            print("  diskSize: \(details.diskSize)")
            print("  display: \(details.display)")
            print("  status: \(details.status)")
            print("  vncUrl: \(String(describing: details.vncUrl))")
            print("  ipAddress: \(String(describing: details.ipAddress))")
            print("  locationName: \(details.locationName)")

            // Serialize the VM details
            print("About to serialize VM details")
            let response = try HTTPResponse.json(vm.details)
            print("Successfully serialized VM details")
            return response

        } catch {
            // This will catch errors from both vmController.get and the json serialization
            print("ERROR: Failed to get VM details: \(error.localizedDescription)")
            return .badRequest(message: error.localizedDescription)
        }
    }

    func handleCreateVM(_ body: Data?) async throws -> HTTPResponse {
        guard let body = body,
            let request = try? JSONDecoder().decode(CreateVMRequest.self, from: body)
        else {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: "Invalid request body"))
            )
        }

        do {
            let sizes = try request.parse()
            let vmController = LumeController()
            try await vmController.create(
                name: request.name,
                os: request.os,
                diskSize: sizes.diskSize,
                cpuCount: request.cpu,
                memorySize: sizes.memory,
                display: request.display,
                ipsw: request.ipsw,
                storage: request.storage
            )

            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode([
                    "message": "VM created successfully", "name": request.name,
                ])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handleDeleteVM(name: String, storage: String? = nil) async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            try await vmController.delete(name: name, storage: storage)
            return HTTPResponse(
                statusCode: .ok, headers: ["Content-Type": "application/json"], body: Data())
        } catch {
            return HTTPResponse(
                statusCode: .badRequest, headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription)))
        }
    }

    func handleCloneVM(_ body: Data?) async throws -> HTTPResponse {
        guard let body = body,
            let request = try? JSONDecoder().decode(CloneRequest.self, from: body)
        else {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: "Invalid request body"))
            )
        }

        do {
            let vmController = LumeController()
            try vmController.clone(
                name: request.name,
                newName: request.newName,
                sourceLocation: request.sourceLocation,
                destLocation: request.destLocation
            )

            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode([
                    "message": "VM cloned successfully",
                    "source": request.name,
                    "destination": request.newName,
                ])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    // MARK: - VM Operation Handlers

    func handleSetVM(name: String, body: Data?) async throws -> HTTPResponse {
        guard let body = body,
            let request = try? JSONDecoder().decode(SetVMRequest.self, from: body)
        else {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: "Invalid request body"))
            )
        }

        do {
            let vmController = LumeController()
            let sizes = try request.parse()
            try vmController.updateSettings(
                name: name,
                cpu: request.cpu,
                memory: sizes.memory,
                diskSize: sizes.diskSize,
                display: sizes.display?.string,
                storage: request.storage
            )

            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(["message": "VM settings updated successfully"])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handleStopVM(name: String, storage: String? = nil) async throws -> HTTPResponse {
        Logger.info(
            "Stopping VM", metadata: ["name": name, "storage": String(describing: storage)])

        do {
            Logger.info("Creating VM controller", metadata: ["name": name])
            let vmController = LumeController()

            Logger.info("Calling stopVM on controller", metadata: ["name": name])
            try await vmController.stopVM(name: name, storage: storage)

            Logger.info(
                "VM stopped, waiting 5 seconds for locks to clear", metadata: ["name": name])

            // Add a delay to ensure locks are fully released before returning
            for i in 1...5 {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                Logger.info("Lock clearing delay", metadata: ["name": name, "seconds": "\(i)/5"])
            }

            // Verify the VM is really in a stopped state
            Logger.info("Verifying VM is stopped", metadata: ["name": name])
            let vm = try? vmController.get(name: name, storage: storage)
            if let vm = vm, vm.details.status == "running" {
                Logger.info(
                    "VM still reports as running despite stop operation",
                    metadata: ["name": name, "severity": "warning"])
            } else {
                Logger.info(
                    "Verification complete: VM is in stopped state", metadata: ["name": name])
            }

            Logger.info("Returning successful response", metadata: ["name": name])
            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(["message": "VM stopped successfully"])
            )
        } catch {
            Logger.error(
                "Failed to stop VM",
                metadata: [
                    "name": name,
                    "error": error.localizedDescription,
                    "storage": String(describing: storage),
                ])
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handleRunVM(name: String, body: Data?) async throws -> HTTPResponse {
        Logger.info("Running VM", metadata: ["name": name])

        // Log the raw body data if available
        if let body = body, let bodyString = String(data: body, encoding: .utf8) {
            Logger.info("Run VM raw request body", metadata: ["name": name, "body": bodyString])
        } else {
            Logger.info("No request body or could not decode as string", metadata: ["name": name])
        }

        do {
            Logger.info("Creating VM controller and parsing request", metadata: ["name": name])
            let request =
                body.flatMap { try? JSONDecoder().decode(RunVMRequest.self, from: $0) }
                ?? RunVMRequest(
                    noDisplay: nil, sharedDirectories: nil, recoveryMode: nil, storage: nil)

            Logger.info(
                "Parsed request",
                metadata: [
                    "name": name,
                    "noDisplay": String(describing: request.noDisplay),
                    "sharedDirectories": "\(request.sharedDirectories?.count ?? 0)",
                    "storage": String(describing: request.storage),
                ])

            Logger.info("Parsing shared directories", metadata: ["name": name])
            let dirs = try request.parse()
            Logger.info(
                "Successfully parsed shared directories",
                metadata: ["name": name, "count": "\(dirs.count)"])

            // Start VM in background
            Logger.info("Starting VM in background", metadata: ["name": name])
            startVM(
                name: name,
                noDisplay: request.noDisplay ?? false,
                sharedDirectories: dirs,
                recoveryMode: request.recoveryMode ?? false,
                storage: request.storage
            )
            Logger.info("VM start initiated in background", metadata: ["name": name])

            // Return response immediately
            return HTTPResponse(
                statusCode: .accepted,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode([
                    "message": "VM start initiated",
                    "name": name,
                    "status": "pending",
                ])
            )
        } catch {
            Logger.error(
                "Failed to run VM",
                metadata: [
                    "name": name,
                    "error": error.localizedDescription,
                ])
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    // MARK: - Image Management Handlers

    func handleIPSW() async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            let url = try await vmController.getLatestIPSWURL()
            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(["url": url.absoluteString])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handlePull(_ body: Data?) async throws -> HTTPResponse {
        guard let body = body,
            let request = try? JSONDecoder().decode(PullRequest.self, from: body)
        else {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: "Invalid request body"))
            )
        }

        do {
            let vmController = LumeController()
            try await vmController.pullImage(
                image: request.image,
                name: request.name,
                registry: request.registry,
                organization: request.organization,
                storage: request.storage
            )

            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode([
                    "message": "Image pulled successfully",
                    "image": request.image,
                    "name": request.name ?? "default",
                ])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handlePruneImages() async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            try await vmController.pruneImages()
            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(["message": "Successfully removed cached images"])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handlePush(_ body: Data?) async throws -> HTTPResponse {
        guard let body = body,
            let request = try? JSONDecoder().decode(PushRequest.self, from: body)
        else {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: "Invalid request body"))
            )
        }

        // Trigger push asynchronously, return Accepted immediately
        Task.detached { @MainActor @Sendable in
            do {
                let vmController = LumeController()
                try await vmController.pushImage(
                    name: request.name,
                    imageName: request.imageName,
                    tags: request.tags,
                    registry: request.registry,
                    organization: request.organization,
                    storage: request.storage,
                    chunkSizeMb: request.chunkSizeMb,
                    verbose: false,  // Verbose typically handled by server logs
                    dryRun: false,  // Default API behavior is likely non-dry-run
                    reassemble: false  // Default API behavior is likely non-reassemble
                )
                print(
                    "Background push completed successfully for image: \(request.imageName):\(request.tags.joined(separator: ","))"
                )
            } catch {
                print(
                    "Background push failed for image: \(request.imageName):\(request.tags.joined(separator: ",")) - Error: \(error.localizedDescription)"
                )
            }
        }

        return HTTPResponse(
            statusCode: .accepted,
            headers: ["Content-Type": "application/json"],
            body: try JSONEncoder().encode([
                "message": AnyEncodable("Push initiated in background"),
                "name": AnyEncodable(request.name),
                "imageName": AnyEncodable(request.imageName),
                "tags": AnyEncodable(request.tags),
            ])
        )
    }

    func handleGetImages(_ request: HTTPRequest) async throws -> HTTPResponse {
        let pathAndQuery = request.path.split(separator: "?", maxSplits: 1)
        let queryParams =
            pathAndQuery.count > 1
            ? pathAndQuery[1]
                .split(separator: "&")
                .reduce(into: [String: String]()) { dict, param in
                    let parts = param.split(separator: "=", maxSplits: 1)
                    if parts.count == 2 {
                        dict[String(parts[0])] = String(parts[1])
                    }
                } : [:]

        let organization = queryParams["organization"] ?? "trycua"

        do {
            let vmController = LumeController()
            let imageList = try await vmController.getImages(organization: organization)

            // Create a response format that matches the CLI output
            let response = imageList.local.map {
                [
                    "repository": $0.repository,
                    "imageId": $0.imageId,
                ]
            }

            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(response)
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    // MARK: - Config Management Handlers

    func handleGetConfig() async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            let settings = vmController.getSettings()
            return try .json(settings)
        } catch {
            return .badRequest(message: error.localizedDescription)
        }
    }

    struct ConfigRequest: Codable {
        let homeDirectory: String?
        let cacheDirectory: String?
        let cachingEnabled: Bool?
    }

    func handleUpdateConfig(_ body: Data?) async throws -> HTTPResponse {
        guard let body = body,
            let request = try? JSONDecoder().decode(ConfigRequest.self, from: body)
        else {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: "Invalid request body"))
            )
        }

        do {
            let vmController = LumeController()

            if let homeDir = request.homeDirectory {
                try vmController.setHomeDirectory(homeDir)
            }

            if let cacheDir = request.cacheDirectory {
                try vmController.setCacheDirectory(path: cacheDir)
            }

            if let cachingEnabled = request.cachingEnabled {
                try vmController.setCachingEnabled(cachingEnabled)
            }

            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(["message": "Configuration updated successfully"])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handleGetLocations() async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            let locations = vmController.getLocations()
            return try .json(locations)
        } catch {
            return .badRequest(message: error.localizedDescription)
        }
    }

    struct LocationRequest: Codable {
        let name: String
        let path: String
    }

    func handleAddLocation(_ body: Data?) async throws -> HTTPResponse {
        guard let body = body,
            let request = try? JSONDecoder().decode(LocationRequest.self, from: body)
        else {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: "Invalid request body"))
            )
        }

        do {
            let vmController = LumeController()
            try vmController.addLocation(name: request.name, path: request.path)

            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode([
                    "message": "Location added successfully",
                    "name": request.name,
                    "path": request.path,
                ])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handleRemoveLocation(_ name: String) async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            try vmController.removeLocation(name: name)
            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(["message": "Location removed successfully"])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    func handleSetDefaultLocation(_ name: String) async throws -> HTTPResponse {
        do {
            let vmController = LumeController()
            try vmController.setDefaultLocation(name: name)
            return HTTPResponse(
                statusCode: .ok,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(["message": "Default location set successfully"])
            )
        } catch {
            return HTTPResponse(
                statusCode: .badRequest,
                headers: ["Content-Type": "application/json"],
                body: try JSONEncoder().encode(APIError(message: error.localizedDescription))
            )
        }
    }

    // MARK: - Log Handlers

    func handleGetLogs(type: String?, lines: Int?) async throws -> HTTPResponse {
        do {
            let logType = type?.lowercased() ?? "all"
            let infoPath = "/tmp/lume_daemon.log"
            let errorPath = "/tmp/lume_daemon.error.log"

            let fileManager = FileManager.default
            var response: [String: String] = [:]

            // Function to read log files
            func readLogFile(path: String) -> String? {
                guard fileManager.fileExists(atPath: path) else {
                    return nil
                }

                do {
                    let content = try String(contentsOfFile: path, encoding: .utf8)

                    // If lines parameter is provided, return only the specified number of lines from the end
                    if let lineCount = lines {
                        let allLines = content.components(separatedBy: .newlines)
                        let startIndex = max(0, allLines.count - lineCount)
                        let lastLines = Array(allLines[startIndex...])
                        return lastLines.joined(separator: "\n")
                    }

                    return content
                } catch {
                    return "Error reading log file: \(error.localizedDescription)"
                }
            }

            // Get logs based on requested type
            if logType == "info" || logType == "all" {
                response["info"] = readLogFile(path: infoPath) ?? "Info log file not found"
            }

            if logType == "error" || logType == "all" {
                response["error"] = readLogFile(path: errorPath) ?? "Error log file not found"
            }

            return try .json(response)
        } catch {
            return .badRequest(message: error.localizedDescription)
        }
    }

    // MARK: - Private Helper Methods

    nonisolated private func startVM(
        name: String,
        noDisplay: Bool,
        sharedDirectories: [SharedDirectory] = [],
        recoveryMode: Bool = false,
        storage: String? = nil
    ) {
        Logger.info(
            "Starting VM in detached task",
            metadata: [
                "name": name,
                "noDisplay": "\(noDisplay)",
                "recoveryMode": "\(recoveryMode)",
                "storage": String(describing: storage),
            ])

        Task.detached { @MainActor @Sendable in
            Logger.info("Background task started for VM", metadata: ["name": name])
            do {
                Logger.info("Creating VM controller in background task", metadata: ["name": name])
                let vmController = LumeController()

                Logger.info(
                    "Calling runVM on controller",
                    metadata: [
                        "name": name,
                        "noDisplay": "\(noDisplay)",
                    ])
                try await vmController.runVM(
                    name: name,
                    noDisplay: noDisplay,
                    sharedDirectories: sharedDirectories,
                    recoveryMode: recoveryMode,
                    storage: storage
                )
                Logger.info("VM started successfully in background task", metadata: ["name": name])
            } catch {
                Logger.error(
                    "Failed to start VM in background task",
                    metadata: [
                        "name": name,
                        "error": error.localizedDescription,
                    ])
            }
        }
        Logger.info("Background task dispatched for VM", metadata: ["name": name])
    }
}
