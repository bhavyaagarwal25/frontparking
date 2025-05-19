#include <iostream>
#include <vector>
#include <unordered_map>
#include <queue>
#include <set>
#include <string>
#include <limits>
#include <algorithm>
using namespace std;
using Graph = unordered_map<string, vector<pair<string, int>>>;
struct Slot {
    int distance;
    string id;

    bool operator>(const Slot& other) const {
        return distance > other.distance;
    }
};
// Simple helper to get distance from Entry by slot prefix letter
int getDistanceFromEntry(const string& slotId) {
    if (slotId.empty()) return numeric_limits<int>::max();
    char prefix = slotId[0];
    switch(prefix) {
        case 'A': return 1;
        case 'B': return 2;
        case 'C': return 3;
        case 'D': return 4;
        case 'E': return 5;
        default: return numeric_limits<int>::max();
    }
}
pair<int, vector<string>> dijkstra(const Graph& graph, const string& start, const string& end) {
    using PQElement = pair<int, pair<string, vector<string>>>;
    priority_queue<PQElement, vector<PQElement>, greater<PQElement>> pq;
    set<string> visited;
    pq.push({0, {start, {start}}});
    while (!pq.empty()) {
        auto [cost, node_path] = pq.top();
        pq.pop();
        string node = node_path.first;
        vector<string> path = node_path.second;
        if (node == end) {
            return {cost, path};
        }
        if (visited.count(node)) continue;
        visited.insert(node);
        auto it = graph.find(node);
        if (it != graph.end()) {
            for (auto& [neighbor, weight] : it->second) {
                if (!visited.count(neighbor)) {
                    vector<string> newPath = path;
                    newPath.push_back(neighbor);
                    pq.push({cost + weight, {neighbor, newPath}});
                }
            }
        }
    }
    return {numeric_limits<int>::max(), {}};
}
class ParkingAllocator {
private:
    Graph graph;
    priority_queue<Slot, vector<Slot>, greater<Slot>> free_slots;
    set<string> allocated_slots;
public:
     ParkingAllocator() {
        // Create directed edges: Entry → Slot, Slot → Exit
        for (char section = 'A'; section <= 'E'; ++section) {
            int weight = section - 'A' + 1;  // A=1, B=2, ..., E=5
            for (int i = 1; i <= 10; ++i) {
                string slotId = string(1, section) + to_string(i);
                // Directed edge from Entry to slot
                graph["Entry"].push_back({slotId, weight});
                // Directed edge from slot to Exit
                graph[slotId].push_back({"Exit", 6 - weight});  // You can customize this cost
                // Add to free slots
                free_slots.push({weight, slotId});
            }
        }
    }

    string allocateSlot(const string& plateNumber) {
        while (!free_slots.empty()) {
            Slot slot = free_slots.top();
            free_slots.pop();
            if (allocated_slots.find(slot.id) == allocated_slots.end()) {
                allocated_slots.insert(slot.id);
                cout << "Allocated slot " << slot.id << " to plate " << plateNumber << endl;
                return slot.id;
            }
        }
        return ""; // no free slot
    }
    vector<string> getShortestPath(const string& slotId) {
        auto [distEntryToSlot, pathEntryToSlot] = dijkstra(graph, "Entry", slotId);
        auto [distSlotToExit, pathSlotToExit] = dijkstra(graph, slotId, "Exit");

        if (pathEntryToSlot.empty() || pathSlotToExit.empty()) return {};

        // Merge paths, avoid duplicate slot node
        pathEntryToSlot.insert(pathEntryToSlot.end(), pathSlotToExit.begin() + 1, pathSlotToExit.end());
        return pathEntryToSlot;
    }
};
int main(int argc, char* argv[]) {
   if (argc < 2) {
    cerr << "Error: Vehicle number is required.\nUsage: ./parking <vehicleNumber>\n";
    return 1;
}
   // string vehicle = argv[1];
    ParkingAllocator allocator;
    string plate = argv[1];

    string slot = allocator.allocateSlot(plate);

    vector<string> path = allocator.getShortestPath(slot);
     if (slot.empty()) {
    cout << "No free slots available for vehicle " << plate << endl;
    return 1;
    }

    cout << "Best Slot: " << slot<< std::endl;
    cout << "Path from entry: ";
    for (const auto& loc : path) {
        std::cout << loc << " ";
    }
    std::cout << std::endl;
    vector<string> shortestpath = allocator.getShortestPath(slot);

    cout << "Plate Number: " << plate << "\nAllocated Slot: " << slot << "\nPath: ";
    for (size_t i = 0; i < shortestpath.size(); i++) {
        cout << shortestpath[i];
        if (i != shortestpath.size() - 1) cout << " -> ";
    }
    cout << endl;

    return 0;}
