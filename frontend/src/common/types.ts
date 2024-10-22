export interface Document {
  documentId: string; // Use camelCase for consistency
  projectId: string; //link the file to a specific project
  userId: string;     // Use camelCase for consistency
  fileName: string;   // Use camelCase for consistency
  fileSize: number;   // Change to number if it's a numeric value
  docStatus: string;  // Use camelCase for consistency
  created: string;    // Consider using Date type if it’s a date
  pages: number;      // Change to number if it's a numeric value
}

export interface Conversation {
  conversationId: string; // Use camelCase for consistency
  document: Document | Document[]; // This allows for a single Document or an array
  messages: Message[]; // Use a separate interface for messages
}

export interface Message {
  type: string;
  data: {
    content: string;
    example: boolean;
    additionalKwargs: Record<string, any>; // More generic for additional kwargs
  };
}


export interface Project {
  projectId: string;          // Unique identifier for the project
  projectName: string;        // Name of the project
  userId: string;             // User who owns or created the project
  created: string;            // Date when the project was created (Consider using Date type)
  description?: string;       // Optional description of the project
  documents: Document | Document[];      // List of documents associated with this project
  conversations: Conversation | Conversation[]
}
