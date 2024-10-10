export interface Document {
  documentId: string; // Use camelCase for consistency
  userId: string;     // Use camelCase for consistency
  fileName: string;   // Use camelCase for consistency
  fileSize: number;   // Change to number if it's a numeric value
  docStatus: string;  // Use camelCase for consistency
  created: string;    // Consider using Date type if it’s a date
  pages: number;      // Change to number if it's a numeric value
  conversations: Conversation[]; // Adjusted type reference
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
