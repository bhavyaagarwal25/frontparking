#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <queue>
#include <limits>
#include <algorithm>
#include <fstream>
#include <set>

using namespace std;

class Graph {
public:
    Graph() {}

    void addNode(const string& nodeName) {
        if (nodeToId.find(nodeName) == nodeToId.end()) {
            nodeToId[nodeName] = nextId;
            idToNode.push_back(nodeName);
            adjList.emplace_back();
            nextId++;
        }
    }

    void addEdge(const string& from, const string& to, int weight) {
        addNode(from);
        addNode(to);
        int fromId = nodeToId[from];
        int toId = nodeToId[to];
        adjList[fromId].push_back({toId, weight});
    }

    void dijkstra(int source, vector<int>& dist, vector<int>& parent) {
        int n = (int)adjList.size();
        dist.assign(n, numeric_limits<int>::max());
        parent.assign(n, -1);
        dist[source] = 0;
        using P = pair<int, int>;
        priority_queue<P, vector<P>, greater<P>> pq;
        pq.push({0, source});

        while (!pq.empty()) {
            auto top = pq.top();
            pq.pop();
            int currDist = top.first;
            int u = top.second;
            if (currDist > dist[u]) continue;
            for (auto& edge : adjList[u]) {
                int v = edge.first;
                int w = edge.second;
                int newDist = currDist + w;
                if (newDist < dist[v]) {
                    dist[v] = newDist;
                    parent[v] = u;
                    pq.push({newDist, v});
                }
            }
        }
    }

    vector<int> reconstructPath(int target, const vector<int>& parent) {
        vector<int> path;
        for (int at = target; at != -1; at = parent[at])
            path.push_back(at);
        reverse(path.begin(), path.end());
        return path;
    }

    int getNodeId(const string& name) {
        return nodeToId.at(name);
    }

    string getNodeName(int id) {
        return idToNode[id];
    }

    int getEdgeWeight(int from, int to) {
        for (const auto& edge : adjList[from]) {
            if (edge.first == to) {
                return edge.second;
            }
        }
        return -1;
    }

private:
    int nextId = 0;
    unordered_map<string, int> nodeToId;
    vector<string> idToNode;
    vector<vector<pair<int,int>>> adjList;
};

set<string> getAllocatedSlots(const string& filename) {
    set<string> allocated;
    ifstream file(filename);
    string plate, slot;
    while (file >> plate >> slot) {
        allocated.insert(slot);
    }
    return allocated;
}

void saveAllocation(const string& filename, const string& plate, const string& slot) {
    ofstream file(filename, ios::app);
    file << plate << " " << slot << endl;
}


int main(int argc, char* argv[]) {
    if (argc != 2) {
        cout << "{ \"error\": \"Usage: ./parking <plate_number>\" }" << endl;
        return 1;
    }

    string plate = argv[1];
    Graph g;
    constexpr int slotsPerRow = 10;
    const vector<char> rows = {'a','b','c','d','e'};

    g.addNode("Entry");
    g.addNode("Exit");
    for (char r : rows)
        for (int i = 1; i <= slotsPerRow; i++)
            g.addNode(string(1, r) + to_string(i));

    for (size_t i = 0; i < rows.size(); i++)
        g.addEdge("Entry", string(1, rows[i]) + "1", (int)i + 1);

    for (char r : rows)
        for (int i = 1; i < slotsPerRow; i++)
            g.addEdge(string(1, r) + to_string(i), string(1, r) + to_string(i + 1), 1);

    for (char r : rows) {
        g.addEdge(string(1, r) + "1", string(1, r) + "6", 1);
        g.addEdge(string(1, r) + "5", string(1, r) + "10", 1);
    }

    for (size_t i = 0; i < rows.size(); i++)
        g.addEdge(string(1, rows[i]) + "10", "Exit", (int)i + 1);

    int entryId = g.getNodeId("Entry");
    vector<int> dist, parent;
    g.dijkstra(entryId, dist, parent);

    set<string> alreadyAllocated = getAllocatedSlots("slots.txt");

    vector<pair<int, string>> slots;
            // for (char r : rows)
            //     for (int i = 1; i <= slotsPerRow; i++)
            //         slots.push_back({dist[g.getNodeId(string(1, r) + to_string(i))], g.getNodeId(string(1, r) + to_string(i))});
    for (char r : rows) {
        string row1 = string(1, r) + "1";
        int row1Id = g.getNodeId(row1);

        g.dijkstra(entryId, dist, parent);
        int entryToRow = dist[row1Id];

        g.dijkstra(row1Id, dist, parent);

        for (int i = 1; i <= slotsPerRow; i++) {
            string slotName = string(1, r) + to_string(i);
            int slotId = g.getNodeId(slotName);
            int totalCost = entryToRow + dist[slotId];
            slots.push_back({totalCost, slotName});
        }
    }
    sort(slots.begin(), slots.end());

    // string finalSlotName = "";
    // for (auto& p : slots) {
    //     if (alreadyAllocated.find(p.second) == alreadyAllocated.end()) {
    //         finalSlotName = p.second;
    //         break;
    //     }
    // }

    //  if (finalSlotName == "") {
    //     cout << "{ \"error\": \"No slots available\" }" << endl;
    //     return 1;
    // }

    // saveAllocation("C:\\Users\\Gaurav Negi\\Desktop\\aa\\frontparking\\number_plate_detection\\slots.txt", plate, finalSlotName);
    
    string finalSlotName = "";

// 🧠 First, check if plate already has a slot assigned
ifstream checkFile("slots.txt");
string existingPlate, existingSlot;
bool alreadyExists = false;

while (checkFile >> existingPlate >> existingSlot) {
    if (existingPlate == plate) {
        finalSlotName = existingSlot;
        alreadyExists = true;
        break;
    }
}
checkFile.close();

// ✅ If not already assigned, find new available slot
if (!alreadyExists) {
    for (auto& p : slots) {
        if (alreadyAllocated.find(p.second) == alreadyAllocated.end()) {
            finalSlotName = p.second;
            break;
        }
    }

    if (finalSlotName == "") {
        cout << "{ \"error\": \"No slots available\" }" << endl;
        return 1;
    }

    saveAllocation("slots.txt", plate, finalSlotName);
}

    // set<string> alreadyAllocated = getAllocatedSlots("slots.txt");

    char r = finalSlotName[0];
    int slotNum = stoi(finalSlotName.substr(1));
    int row1Id = g.getNodeId(string(1, r) + "1");
    int slotId = g.getNodeId(finalSlotName);
    int exitId = g.getNodeId("Exit");

    g.dijkstra(entryId, dist, parent);
    vector<int> pathEntryToRow1 = g.reconstructPath(row1Id, parent);
    g.dijkstra(row1Id, dist, parent);
    vector<int> pathRow1ToSlot = g.reconstructPath(slotId, parent);

// int slot = -1;
// string slotName;
// for (auto &p : slots) {
//     slotName = g.getNodeName(p.second);
//     if (alreadyAllocated.find(slotName) == alreadyAllocated.end()) {
//         slot = p.second;
//         break;
//     }
// }

// if (slot == -1) {
//     cout << "{ \"error\": \"No slots available\" }" << endl;
//     return 1;
// }

// Save the allocation
// saveAllocation("slots.txt", plate, slotName);
//     char r = slotName[0];
//     int slotNum = stoi(slotName.substr(1));

//     int row1Id = g.getNodeId(string(1, r) + "1");
//     int exitId = g.getNodeId("Exit");

//     g.dijkstra(entryId, dist, parent);
//     vector<int> pathEntryToRow1 = g.reconstructPath(row1Id, parent);
//     g.dijkstra(row1Id, dist, parent);
//     vector<int> pathRow1ToSlot = g.reconstructPath(slot, parent);

    vector<int> fullPath;
    fullPath.insert(fullPath.end(), pathEntryToRow1.begin(), pathEntryToRow1.end() - 1);
    fullPath.insert(fullPath.end(), pathRow1ToSlot.begin(), pathRow1ToSlot.end());

    if (slotNum < 5) {
        for (int i = slotNum + 1; i <= 5; i++)
            fullPath.push_back(g.getNodeId(string(1, r) + to_string(i)));
        fullPath.push_back(g.getNodeId(string(1, r) + "10"));
    } else {
        for (int i = slotNum + 1; i <= 10; i++)
            fullPath.push_back(g.getNodeId(string(1, r) + to_string(i)));
    }

    fullPath.push_back(exitId);

    
    cout << "{ \"plate\": \"" << plate << "\", \"slot\": \"" << finalSlotName << "\", \"path\": [";
    for (size_t i = 0; i < fullPath.size(); i++) {
        cout << "\"" << g.getNodeName(fullPath[i]) << "\"";
        if (i + 1 < fullPath.size()) cout << ", ";
    }
    cout << "] }" << endl;

    return 0;
}